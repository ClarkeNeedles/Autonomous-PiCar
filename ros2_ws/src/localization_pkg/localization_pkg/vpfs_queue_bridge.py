#!/usr/bin/env python3
import json
import math
import time
from typing import Any, Optional

import requests
import rclpy
from geometry_msgs.msg import PoseStamped, Quaternion
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import String


def yaw_to_quaternion(yaw: float) -> Quaternion:
    quat = Quaternion()
    quat.x = 0.0
    quat.y = 0.0
    quat.z = math.sin(yaw / 2.0)
    quat.w = math.cos(yaw / 2.0)
    return quat


class VpfsQueueBridge(Node):
    def __init__(self) -> None:
        super().__init__("vpfs_queue_bridge")

        self.declare_parameter("vpfs_url", "http://192.168.0.100:5000")
        self.declare_parameter("team_id", 46)
        self.declare_parameter("auth", "3aa5fcda383fcfa27a63751a0fa738fc")
        self.declare_parameter("frame_id", "map")
        self.declare_parameter("base_frame_id", "base_link")
        self.declare_parameter("pose_poll_hz", 2.0)
        self.declare_parameter("fares_poll_hz", 1.0)
        self.declare_parameter("request_timeout_sec", 1.0)
        self.declare_parameter("claim_pose_timeout_sec", 5.0)

        self.vpfs_url = str(self.get_parameter("vpfs_url").value).rstrip("/")
        self.team_id = int(self.get_parameter("team_id").value)
        self.auth = str(self.get_parameter("auth").value)
        self.frame_id = str(self.get_parameter("frame_id").value)
        self.base_frame_id = str(self.get_parameter("base_frame_id").value)
        self.pose_poll_hz = float(self.get_parameter("pose_poll_hz").value)
        self.fares_poll_hz = float(self.get_parameter("fares_poll_hz").value)
        self.request_timeout_sec = float(self.get_parameter("request_timeout_sec").value)
        self.claim_pose_timeout_sec = float(
            self.get_parameter("claim_pose_timeout_sec").value
        )

        self.session = requests.Session()

        self.latest_x: Optional[float] = None
        self.latest_y: Optional[float] = None
        self.latest_heading: Optional[float] = None

        self.available_fares: list[dict] = []
        self.current_fare: Optional[dict] = None
        self.best_fare: Optional[dict] = None

        self.odom_pub = self.create_publisher(Odometry, "/odometry/filtered", 10)
        self.pose_pub = self.create_publisher(PoseStamped, "/vpfs/pose", 10)
        self.current_fare_pub = self.create_publisher(String, "/vpfs/current_fare", 10)

        self.pose_timer = self.create_timer(1.0 / self.pose_poll_hz, self.poll_pose)
        self.fares_timer = self.create_timer(
            1.0 / self.fares_poll_hz, self.poll_fares_and_manage_queue
        )

        self.get_logger().info(
            "VPFS queue bridge started. url=%s team=%d pose_hz=%.2f fares_hz=%.2f"
            % (self.vpfs_url, self.team_id, self.pose_poll_hz, self.fares_poll_hz)
        )

    def get_json(self, path: str, params: Optional[dict] = None) -> Optional[Any]:
        url = f"{self.vpfs_url}{path}"
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.request_timeout_sec,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            self.get_logger().warn(f"GET failed {url}: {exc}")
            return None
        except ValueError as exc:
            self.get_logger().warn(f"Bad JSON from {url}: {exc}")
            return None

    def extract_fare_list(self, fares_payload: Any) -> list[dict]:
        if isinstance(fares_payload, list):
            return fares_payload
        if isinstance(fares_payload, dict):
            if isinstance(fares_payload.get("fares"), list):
                return fares_payload["fares"]
            if isinstance(fares_payload.get("available_fares"), list):
                return fares_payload["available_fares"]
        return []

    def extract_current_fare_object(self, payload: Any) -> Optional[dict]:
        if not isinstance(payload, dict):
            return None

        if isinstance(payload.get("fare"), dict):
            return payload["fare"]

        if isinstance(payload.get("current_fare"), dict):
            return payload["current_fare"]

        if self.extract_fare_id(payload) is not None:
            return payload

        return None

    def extract_fare_id(self, fare: dict) -> Optional[int]:
        try:
            return int(fare["id"])
        except (KeyError, TypeError, ValueError):
            return None

    def extract_fare_value(self, fare: dict) -> Optional[float]:
        try:
            return float(fare["pay"])
        except (KeyError, TypeError, ValueError):
            return None

    def extract_fare_reputation(self, fare: dict) -> Optional[int]:
        try:
            return int(fare["reputation"])
        except (KeyError, TypeError, ValueError):
            return None

    def extract_pickup_xy(self, fare: dict) -> Optional[tuple[float, float]]:
        try:
            src = fare["src"]
            return float(src["x"]), float(src["y"])
        except (KeyError, TypeError, ValueError):
            return None

    def extract_dropoff_xy(self, fare: dict) -> Optional[tuple[float, float]]:
        try:
            dest = fare["dest"]
            return float(dest["x"]), float(dest["y"])
        except (KeyError, TypeError, ValueError):
            return None

    def extract_bool(self, fare: dict, key: str) -> bool:
        value = fare.get(key, False)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() == "true"
        return False

    def is_fare_claimed(self, fare: dict) -> bool:
        return bool(fare.get("claimed", False))

    def is_fare_expired(self, fare: dict) -> bool:
        try:
            return float(fare["expiry"]) <= time.time()
        except (KeyError, TypeError, ValueError):
            return True

    def normalize_current_fare(self, fare: Optional[dict]) -> Optional[dict]:
        if fare is None:
            return None

        fare_id = self.extract_fare_id(fare)
        pickup = self.extract_pickup_xy(fare)
        dropoff = self.extract_dropoff_xy(fare)
        if fare_id is None or pickup is None or dropoff is None:
            return None

        return {
            "id": fare_id,
            "src": {"x": pickup[0], "y": pickup[1]},
            "dest": {"x": dropoff[0], "y": dropoff[1]},
            "inPosition": self.extract_bool(fare, "inPosition"),
            "pickedUp": self.extract_bool(fare, "pickedUp"),
            "completed": self.extract_bool(fare, "completed"),
        }

    def publish_current_fare(self, status: str) -> None:
        payload = {
            "fare": self.current_fare,
            "status": status,
        }
        msg = String()
        msg.data = json.dumps(payload)
        self.current_fare_pub.publish(msg)

    def publish_pose_outputs(self, x: float, y: float, heading: float) -> None:
        stamp = self.get_clock().now().to_msg()
        quat = yaw_to_quaternion(heading)

        pose_msg = PoseStamped()
        pose_msg.header.stamp = stamp
        pose_msg.header.frame_id = self.frame_id
        pose_msg.pose.position.x = x
        pose_msg.pose.position.y = y
        pose_msg.pose.position.z = 0.0
        pose_msg.pose.orientation = quat
        self.pose_pub.publish(pose_msg)

        odom_msg = Odometry()
        odom_msg.header.stamp = stamp
        odom_msg.header.frame_id = self.frame_id
        odom_msg.child_frame_id = self.base_frame_id
        odom_msg.pose.pose.position.x = x
        odom_msg.pose.pose.position.y = y
        odom_msg.pose.pose.position.z = 0.0
        odom_msg.pose.pose.orientation = quat
        odom_msg.twist.twist.linear.x = 0.0
        odom_msg.twist.twist.angular.z = 0.0
        odom_msg.pose.covariance = [
            0.05, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.05, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 9999.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 9999.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 9999.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.1,
        ]
        odom_msg.twist.covariance = [
            0.1, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.1, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 9999.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 9999.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 9999.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.2,
        ]
        self.odom_pub.publish(odom_msg)

    def refresh_pose_once(self) -> bool:
        data = self.get_json(
            f"/whereami/{self.team_id}",
            params={"auth": self.auth},
        )
        if data is None:
            return False

        position = data.get("position")
        if position is None:
            self.get_logger().warn(
                f"Missing position field from /whereami response. Full response: {data}"
            )
            return False

        try:
            x = float(position["x"])
            y = float(position["y"])
            heading = float(position["heading"])
        except (KeyError, TypeError, ValueError) as exc:
            self.get_logger().warn(f"Malformed /whereami payload: {data} ({exc})")
            return False

        self.latest_x = x
        self.latest_y = y
        self.latest_heading = heading
        self.publish_pose_outputs(x, y, heading)
        return True

    def wait_for_claim_pose(self) -> bool:
        deadline = time.monotonic() + self.claim_pose_timeout_sec
        while time.monotonic() < deadline:
            if self.refresh_pose_once():
                return True
            time.sleep(0.25)
        return False

    def compute_fare_score(self, fare: dict) -> float:
        if self.latest_x is None or self.latest_y is None:
            return -1.0

        if self.is_fare_claimed(fare) or self.is_fare_expired(fare):
            return -1.0

        pickup = self.extract_pickup_xy(fare)
        dropoff = self.extract_dropoff_xy(fare)
        value = self.extract_fare_value(fare)
        reputation = self.extract_fare_reputation(fare)
        if pickup is None or dropoff is None or value is None or reputation is None:
            return -1.0

        px, py = pickup
        dx, dy = dropoff
        robot_to_pickup = math.hypot(px - self.latest_x, py - self.latest_y)
        pickup_to_dropoff = math.hypot(dx - px, dy - py)
        total_distance = max(robot_to_pickup + pickup_to_dropoff, 1e-6)

        reward = value + (0.5 * reputation)
        return reward / total_distance

    def recompute_best_fare(self) -> None:
        best_fare = None
        best_score = -1.0

        for fare in self.available_fares:
            score = self.compute_fare_score(fare)
            if score > best_score:
                best_score = score
                best_fare = fare

        self.best_fare = best_fare

    def refresh_current_fare(self) -> bool:
        payload = self.get_json(
            f"/fares/current/{self.team_id}",
            params={"auth": self.auth},
        )
        if payload is None:
            return False

        fare_obj = self.extract_current_fare_object(payload)
        self.current_fare = self.normalize_current_fare(fare_obj)
        return True

    def claim_best_fare(self) -> bool:
        if self.best_fare is None:
            self.get_logger().warn("No best fare available to claim.")
            self.publish_current_fare("claim_failed")
            return False

        fare_id = self.extract_fare_id(self.best_fare)
        if fare_id is None:
            self.get_logger().warn("Best fare has no valid id.")
            self.publish_current_fare("claim_failed")
            return False

        result = self.get_json(
            f"/fares/claim/{fare_id}",
            params={"auth": self.auth},
        )
        if result is None:
            self.publish_current_fare("claim_failed")
            return False

        success = bool(result.get("success", False)) if isinstance(result, dict) else False
        message = result.get("message", "") if isinstance(result, dict) else ""
        if not success:
            self.get_logger().warn(f"Failed to claim fare {fare_id}: {message}")
            self.publish_current_fare("claim_failed")
            return False

        self.get_logger().info(f"Claimed fare {fare_id}: {message}")

        claimed_fare = self.normalize_current_fare(self.best_fare)
        if claimed_fare is not None:
            self.current_fare = claimed_fare

        if not self.refresh_current_fare():
            self.get_logger().warn(
                "Claim succeeded, but current fare refresh failed. Using claimed fare locally."
            )

        self.publish_current_fare("active")
        return True

    def poll_pose(self) -> None:
        self.refresh_pose_once()

    def poll_fares_and_manage_queue(self) -> None:
        current_ok = self.refresh_current_fare()
        if not current_ok:
            if self.current_fare is not None:
                self.publish_current_fare("active")
            else:
                self.publish_current_fare("idle")
            self.get_logger().warn(
                "Skipping auto-claim because the current fare check failed."
            )
            return

        if self.current_fare is not None:
            self.publish_current_fare("active")
            return

        self.current_fare = None
        self.publish_current_fare("idle")

        if not self.wait_for_claim_pose():
            self.get_logger().warn(
                "Timed out after %.1f seconds waiting for current VPFS pose; skipping auto-claim."
                % self.claim_pose_timeout_sec
            )
            return

        fares_payload = self.get_json("/fares")
        if fares_payload is None:
            return

        self.available_fares = self.extract_fare_list(fares_payload)
        self.recompute_best_fare()
        if self.best_fare is None:
            self.get_logger().info(
                "No claimable fare available right now.",
                throttle_duration_sec=10.0,
            )
            return

        self.claim_best_fare()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VpfsQueueBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.session.close()
        node.destroy_node()
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
