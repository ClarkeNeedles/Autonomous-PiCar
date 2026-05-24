#!/usr/bin/env python3
import json
import math
import time
from typing import Any, Optional

import requests
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, Quaternion
from std_msgs.msg import String, Bool


class VpfsInterfaceNode(Node):
    def __init__(self) -> None:
        super().__init__("vpfs_interface_node")

        # ---------------- Parameters ----------------
        self.declare_parameter("vpfs_url", "http://192.168.0.100:5000")
        self.declare_parameter("team_id", 46)
        self.declare_parameter("auth", "3aa5fcda383fcfa27a63751a0fa738fc")
        self.declare_parameter("frame_id", "map")

        self.declare_parameter("pose_poll_hz", 2.0)
        self.declare_parameter("fares_poll_hz", 1.0)
        self.declare_parameter("request_timeout_sec", 1.0)

        self.vpfs_url = str(self.get_parameter("vpfs_url").value).rstrip("/")
        self.team_id = int(self.get_parameter("team_id").value)
        self.auth = str(self.get_parameter("auth").value)
        self.frame_id = str(self.get_parameter("frame_id").value)

        self.pose_poll_hz = float(self.get_parameter("pose_poll_hz").value)
        self.fares_poll_hz = float(self.get_parameter("fares_poll_hz").value)
        self.request_timeout_sec = float(
            self.get_parameter("request_timeout_sec").value
        )

        # ---------------- HTTP Session ----------------
        self.session = requests.Session()

        # ---------------- Internal State ----------------
        self.latest_x: Optional[float] = None
        self.latest_y: Optional[float] = None
        self.latest_heading: float = 0.0

        self.available_fares: list[dict] = []
        self.current_fare: Optional[dict] = None
        self.best_fare: Optional[dict] = None

        # ---------------- Publishers ----------------
        self.pose_pub = self.create_publisher(PoseStamped, "/vpfs/pose", 10)
        self.current_fare_pub = self.create_publisher(String, "/vpfs/current_fare", 10)

        # ---------------- Subscribers ----------------
        self.claim_best_sub = self.create_subscription(
            Bool,
            "/vpfs/claim_request",
            self.claim_request_callback,
            10,
        )
        self.drop_current_sub = self.create_subscription(
            Bool,
            "/vpfs/drop_request",
            self.drop_current_request_callback,
            10,
        )

        # ---------------- Timers ----------------
        self.pose_timer = self.create_timer(
            1.0 / self.pose_poll_hz, self.poll_pose
        )
        self.fares_timer = self.create_timer(
            1.0 / self.fares_poll_hz, self.poll_fares_and_current_fare
        )

        self.get_logger().info(
            f"VPFS interface started. url={self.vpfs_url}, team={self.team_id}, auth={self.auth}"
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def get_json(self, path: str, params: Optional[dict] = None) -> Optional[Any]:
        url = f"{self.vpfs_url}{path}"
        try:
            resp = self.session.get(
                url,
                params=params,
                timeout=self.request_timeout_sec,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self.get_logger().warn(f"GET failed {url}: {e}")
            return None
        except ValueError as e:
            self.get_logger().warn(f"Bad JSON from {url}: {e}")
            return None

    def publish_current_fare(self, status: str) -> None:
        msg = String()
        msg.data = json.dumps({
            "fare": self.current_fare,
            "status": status
        })
        self.current_fare_pub.publish(msg)

    # -------------------------------------------------------------------------
    # Fare parsing helpers
    # -------------------------------------------------------------------------
    def extract_fare_list(self, fares_payload: Any) -> list[dict]:
        if isinstance(fares_payload, list):
            return fares_payload
        if isinstance(fares_payload, dict):
            if isinstance(fares_payload.get("fares"), list):
                return fares_payload["fares"]
            if isinstance(fares_payload.get("available_fares"), list):
                return fares_payload["available_fares"]
        return []

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

    def extract_fare_modifier(self, fare: dict) -> Optional[int]:
        try:
            return int(fare["modifiers"])
        except (KeyError, TypeError, ValueError):
            return None

    def is_fare_claimed(self, fare: dict) -> bool:
        return bool(fare.get("claimed", False))

    def is_fare_expired(self, fare: dict) -> bool:
        try:
            return float(fare["expiry"]) <= time.time()
        except (KeyError, TypeError, ValueError):
            return True

    def extract_pickup_xy(self, fare: dict) -> Optional[tuple[float, float]]:
        try:
            src = fare["src"]
            return float(src["x"]), float(src["y"])
        except (KeyError, TypeError, ValueError):
            return None

    def extract_dropoff_xy(self, fare: dict) -> Optional[tuple[float, float]]:
        """
        VPFS coordinates are in centimetres from map origin.
        """
        try:
            dest = fare["dest"]
            return float(dest["x"]), float(dest["y"])
        except (KeyError, TypeError, ValueError):
            return None

    def extract_current_fare_object(self, current_fare_payload: Any) -> Optional[dict]:
        if not isinstance(current_fare_payload, dict):
            return None

        if isinstance(current_fare_payload.get("fare"), dict):
            return current_fare_payload["fare"]

        if isinstance(current_fare_payload.get("current_fare"), dict):
            return current_fare_payload["current_fare"]

        if self.extract_fare_id(current_fare_payload) is not None:
            return current_fare_payload

        return None

    # -------------------------------------------------------------------------
    # Fare scoring
    # -------------------------------------------------------------------------
    def compute_fare_score(self, fare: dict) -> float:
        if self.latest_x is None or self.latest_y is None:
            return -1.0

        if self.is_fare_claimed(fare):
            return -1.0

        if self.is_fare_expired(fare):
            return -1.0

        value = self.extract_fare_value(fare)
        reputation = self.extract_fare_reputation(fare)
        pickup = self.extract_pickup_xy(fare)
        dropoff = self.extract_dropoff_xy(fare)

        if value is None or reputation is None or pickup is None or dropoff is None:
            return -1.0

        px, py = pickup
        dx, dy = dropoff

        robot_to_pickup = math.hypot(px - self.latest_x, py - self.latest_y)
        pickup_to_dropoff = math.hypot(dx - px, dy - py)

        total_distance = robot_to_pickup + pickup_to_dropoff
        total_distance = max(total_distance, 1e-6)

        # ---- NEW PART ----
        alpha = 0.5  # tune this
        reward = value + alpha * reputation

        return reward / total_distance

    def recompute_best_fare(self) -> None:
        best = None
        best_score = -1.0

        for fare in self.available_fares:
            score = self.compute_fare_score(fare)
            if score > best_score:
                best_score = score
                best = fare

        self.best_fare = best

        if best is not None:
            fare_id = self.extract_fare_id(best)
            self.get_logger().info(
                f"Best fare updated: id={fare_id}, score={best_score:.3f}"
            )
        else:
            self.get_logger().info("No valid best fare available.")

    # -------------------------------------------------------------------------
    # Polling
    # -------------------------------------------------------------------------
    def poll_pose(self) -> None:
        data = self.get_json(
            f"/whereami/{self.team_id}",
            params={"auth": self.auth},
        )
        if data is None:
            return

        position = data.get("position")
        if position is None:
            return

        try:
            x = float(position["x"])
            y = float(position["y"])
            heading = float(position.get("heading", 0.0))
        except (KeyError, TypeError, ValueError) as e:
            self.get_logger().warn(f"Malformed /whereami payload: {data} ({e})")
            return

        self.latest_x = x
        self.latest_y = y
        self.latest_heading = heading

        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = self.frame_id
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0

        q = Quaternion()
        q.x = 0.0
        q.y = 0.0
        q.z = math.sin(heading / 2.0)
        q.w = math.cos(heading / 2.0)
        pose.pose.orientation = q

        self.pose_pub.publish(pose)

    def poll_fares_and_current_fare(self) -> None:
        fares_payload = self.get_json("/fares")
        if fares_payload is not None:
            self.available_fares = self.extract_fare_list(fares_payload)
            self.recompute_best_fare()

        current_fare_payload = self.get_json(
            f"/fares/current/{self.team_id}",
            params={"auth": self.auth},
        )

        if current_fare_payload is not None:
            self.current_fare = self.extract_current_fare_object(current_fare_payload)

            status = "idle"
            if self.current_fare is not None:
                status = "active"

            self.publish_current_fare(status)

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------
    def claim_request_callback(self, msg: Bool) -> None:
        if not msg.data:
            return

        if self.current_fare is not None:
            self.get_logger().info("Claim ignored: current fare already active.")
            self.publish_current_fare("active")
            return

        if self.best_fare is None:
            self.get_logger().warn("Claim failed: no best fare available.")
            self.publish_current_fare("claim_failed")
            return

        fare_idx = self.extract_fare_id(self.best_fare)
        if fare_idx is None:
            self.get_logger().warn("Claim failed: best fare has no valid id.")
            self.publish_current_fare("claim_failed")
            return

        result = self.get_json(
            f"/fares/claim/{fare_idx}",
            params={"auth": self.auth},
        )
        if result is None:
            self.publish_current_fare("claim_failed")
            return

        success = result.get("success", False) if isinstance(result, dict) else False
        message = result.get("message", "") if isinstance(result, dict) else ""

        if success:
            self.get_logger().info(f"Claimed best fare {fare_idx}: {message}")
            self.poll_fares_and_current_fare()
        else:
            self.get_logger().warn(f"Failed to claim best fare {fare_idx}: {message}")
            self.publish_current_fare("claim_failed")

    def drop_current_request_callback(self, msg: Bool) -> None:
        if not msg.data:
            return

        if self.current_fare is None:
            self.get_logger().info("Drop ignored: no current fare.")
            self.publish_current_fare("idle")
            return

        fare_idx = self.extract_fare_id(self.current_fare)
        if fare_idx is None:
            self.get_logger().warn("Drop failed: current fare has no valid id.")
            self.publish_current_fare("drop_failed")
            return

        result = self.get_json(
            f"/fares/drop/{fare_idx}",
            params={"auth": self.auth},
        )
        if result is None:
            self.publish_current_fare("drop_failed")
            return

        success = result.get("success", False) if isinstance(result, dict) else False
        message = result.get("message", "") if isinstance(result, dict) else ""

        if success:
            self.get_logger().info(f"Dropped current fare {fare_idx}: {message}")
            self.current_fare = None
            self.publish_current_fare("idle")
            self.poll_fares_and_current_fare()
        else:
            self.get_logger().warn(f"Failed to drop current fare {fare_idx}: {message}")
            self.publish_current_fare("drop_failed")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = VpfsInterfaceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.session.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
