#!/usr/bin/env python3
"""
Quick test: subscribe to /segmentation/mask and print class percentages.
Classes: 0=background, 1=green, 2=yellow
Run alongside segmentation_node to verify model output.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np


class MaskChecker(Node):
    def __init__(self):
        super().__init__('mask_checker')
        self.bridge = CvBridge()
        self.create_subscription(Image, '/segmentation/mask', self.cb, 1)
        self.get_logger().info('Listening on /segmentation/mask ...')

    def cb(self, msg):
        mask = self.bridge.imgmsg_to_cv2(msg, 'mono8')
        total = mask.size

        bg    = np.sum(mask == 0) / total * 100
        green = np.sum(mask == 1) / total * 100
        yellow = np.sum(mask == 2) / total * 100

        self.get_logger().info(
            f'background: {bg:5.1f}%  |  green: {green:5.1f}%  |  yellow: {yellow:5.1f}%'
        )


def main():
    rclpy.init()
    rclpy.spin(MaskChecker())


if __name__ == '__main__':
    main()
