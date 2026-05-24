#!/usr/bin/env python3
import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

class StdinToCmdVel(Node):
    def __init__(self):
        super().__init__("stdin_to_cmdvel")
        self.cmd_pub = self.create_publisher(Twist, "/ros_vel", 10)
        self.enable_pub = self.create_publisher(Bool, "/enable", 10)
        self.last_enable = None
        self.get_logger().info("stdin_to_cmdvel running. Expect: 'lin ang enable' per line.")

    def publish_cmd(self, lin: float, ang: float, enable: int):
        # Publish enable on changes (optional, but useful)
        if self.last_enable is None or enable != self.last_enable:
            self.enable_pub.publish(Bool(data=bool(enable)))
            self.last_enable = enable

        # Always publish Twist no matter what enable is
        t = Twist()
        t.linear.x = float(lin)
        t.angular.z = float(ang)
        self.cmd_pub.publish(t)

def main():
    rclpy.init()
    node = StdinToCmdVel()
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) != 3:
                continue

            lin = float(parts[0])
            ang = float(parts[1])
            enable = int(float(parts[2]))

            node.publish_cmd(lin, ang, enable)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
