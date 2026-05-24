#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped, Quaternion
from nav_msgs.msg import Odometry


def clamp_angle(angle: float) -> float:
    """Wrap angle to [-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def yaw_to_quaternion(yaw: float) -> Quaternion:
    """Convert yaw angle to quaternion."""
    q = Quaternion()
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


def quaternion_to_yaw(q: Quaternion) -> float:
    """Extract yaw from quaternion."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class OdometryFusionNode(Node):
    def __init__(self) -> None:
        super().__init__("odometry_fusion_node")

        # Parameters
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("vpfs_pose_topic", "/vpfs/pose")
        self.declare_parameter("odom_topic", "/odometry/filtered")
        self.declare_parameter("odom_frame", "map")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("publish_rate_hz", 20.0)
        self.declare_parameter("vpfs_blend_alpha", 1.0)
        self.declare_parameter("use_vpfs_heading", True)

        cmd_vel_topic = self.get_parameter("cmd_vel_topic").value
        vpfs_pose_topic = self.get_parameter("vpfs_pose_topic").value
        odom_topic = self.get_parameter("odom_topic").value
        self.odom_frame = self.get_parameter("odom_frame").value
        self.base_frame = self.get_parameter("base_frame").value
        publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)
        self.vpfs_blend_alpha = float(self.get_parameter("vpfs_blend_alpha").value)
        self.use_vpfs_heading = bool(self.get_parameter("use_vpfs_heading").value)

        if publish_rate_hz <= 0.0:
            raise ValueError("publish_rate_hz must be > 0")

        if not (0.0 <= self.vpfs_blend_alpha <= 1.0):
            raise ValueError("vpfs_blend_alpha must be between 0.0 and 1.0")

        # Internal state
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0

        self.linear_velocity = 0.0
        self.angular_velocity = 0.0

        self.have_cmd = False
        self.have_vpfs = False

        self.last_update_time = self.get_clock().now()

        # Subscribers
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            cmd_vel_topic,
            self.cmd_vel_callback,
            10,
        )

        self.vpfs_sub = self.create_subscription(
            PoseStamped,
            vpfs_pose_topic,
            self.vpfs_pose_callback,
            10,
        )

        # Publisher
        self.odom_pub = self.create_publisher(Odometry, odom_topic, 10)

        # Timer
        timer_period = 1.0 / publish_rate_hz
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info("Odometry fusion node started")
        self.get_logger().info(f"Subscribing to {cmd_vel_topic}")
        self.get_logger().info(f"Subscribing to {vpfs_pose_topic}")
        self.get_logger().info(f"Publishing odometry to {odom_topic}")

    def cmd_vel_callback(self, msg: Twist) -> None:
        """
        Store latest commanded velocity.
        This node dead-reckons using commanded velocity between VPFS updates.
        """
        self.linear_velocity = msg.linear.x
        self.angular_velocity = msg.angular.z
        self.have_cmd = True

    def vpfs_pose_callback(self, msg: PoseStamped) -> None:
        """
        Correct the current pose estimate using VPFS.
        alpha = 1.0 -> snap directly to VPFS
        alpha < 1.0 -> blend toward VPFS
        """
        vpfs_x = msg.pose.position.x
        vpfs_y = msg.pose.position.y
        vpfs_yaw = quaternion_to_yaw(msg.pose.orientation)

        if not self.have_vpfs:
            # First VPFS update initializes the estimate
            self.x = vpfs_x
            self.y = vpfs_y
            if self.use_vpfs_heading:
                self.yaw = vpfs_yaw
            self.have_vpfs = True
            self.get_logger().info("Received first VPFS pose; odometry initialized.")
            return

        alpha = self.vpfs_blend_alpha

        self.x = (1.0 - alpha) * self.x + alpha * vpfs_x
        self.y = (1.0 - alpha) * self.y + alpha * vpfs_y

        if self.use_vpfs_heading:
            yaw_error = clamp_angle(vpfs_yaw - self.yaw)
            self.yaw = clamp_angle(self.yaw + alpha * yaw_error)

    def timer_callback(self) -> None:
        """
        Integrate motion forward using latest cmd_vel.
        Publish current filtered odometry estimate.
        """
        now = self.get_clock().now()
        dt = (now - self.last_update_time).nanoseconds / 1e9
        self.last_update_time = now

        if dt <= 0.0:
            return

        # Dead reckoning step
        # x_dot = v * cos(yaw)
        # y_dot = v * sin(yaw)
        # yaw_dot = w
        self.x += self.linear_velocity * math.cos(self.yaw) * dt
        self.y += self.linear_velocity * math.sin(self.yaw) * dt
        self.yaw = clamp_angle(self.yaw + self.angular_velocity * dt)

        self.publish_odometry(now)

    def publish_odometry(self, stamp) -> None:
        odom_msg = Odometry()
        odom_msg.header.stamp = stamp.to_msg()
        odom_msg.header.frame_id = self.odom_frame
        odom_msg.child_frame_id = self.base_frame

        odom_msg.pose.pose.position.x = self.x
        odom_msg.pose.pose.position.y = self.y
        odom_msg.pose.pose.position.z = 0.0
        odom_msg.pose.pose.orientation = yaw_to_quaternion(self.yaw)

        odom_msg.twist.twist.linear.x = self.linear_velocity
        odom_msg.twist.twist.angular.z = self.angular_velocity

        # Simple placeholder covariance values
        odom_msg.pose.covariance = [
            0.05, 0.0,  0.0,  0.0, 0.0, 0.0,
            0.0,  0.05, 0.0,  0.0, 0.0, 0.0,
            0.0,  0.0,  9999.0, 0.0, 0.0, 0.0,
            0.0,  0.0,  0.0,  9999.0, 0.0, 0.0,
            0.0,  0.0,  0.0,  0.0, 9999.0, 0.0,
            0.0,  0.0,  0.0,  0.0, 0.0, 0.1,
        ]

        odom_msg.twist.covariance = [
            0.1,  0.0,  0.0,  0.0, 0.0, 0.0,
            0.0,  0.1,  0.0,  0.0, 0.0, 0.0,
            0.0,  0.0,  9999.0, 0.0, 0.0, 0.0,
            0.0,  0.0,  0.0,  9999.0, 0.0, 0.0,
            0.0,  0.0,  0.0,  0.0, 9999.0, 0.0,
            0.0,  0.0,  0.0,  0.0, 0.0, 0.2,
        ]

        self.odom_pub.publish(odom_msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = OdometryFusionNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()