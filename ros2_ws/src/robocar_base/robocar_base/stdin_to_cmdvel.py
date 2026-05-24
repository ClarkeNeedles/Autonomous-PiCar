#!/usr/bin/env python3
import sys
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool


class StdinToCmdVel(Node):
    def __init__(self):
        super().__init__("stdin_to_cmdvel")

        # Publish directly to robot velocity topic
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.enable_pub = self.create_publisher(Bool, "/enable", 10)

        self.last_msg_time = time.time()
        self.timeout_s = 0.5  # safety stop if input stops

        self.timer = self.create_timer(0.05, self.on_timer)
        self.get_logger().info("stdin_to_cmdvel running. Expect lines: '<lin> <ang> <enable>'")

    def on_timer(self):
        # Safety stop if no commands recently
        if (time.time() - self.last_msg_time) > self.timeout_s:
            t = Twist()
            t.linear.x = 0.0
            t.angular.z = 0.0
            self.cmd_pub.publish(t)

    def handle_line(self, line: str):
        parts = line.strip().split()
        if len(parts) != 3:
            return

        lin = float(parts[0])
        ang = float(parts[1])
        enable = int(float(parts[2]))

        self.enable_pub.publish(Bool(data=bool(enable)))

        t = Twist()
        t.linear.x = lin if enable else 0.0
        t.angular.z = ang if enable else 0.0
        self.cmd_pub.publish(t)

        self.last_msg_time = time.time()


def main():
    rclpy.init()
    node = StdinToCmdVel()

    try:
        # Read stdin line by line, publish immediately
        for line in sys.stdin:
            if not line:
                break
            node.handle_line(line)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
