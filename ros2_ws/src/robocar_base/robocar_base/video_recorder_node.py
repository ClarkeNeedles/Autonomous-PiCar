#!/usr/bin/env python3

import os
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class VideoRecorderNode(Node):
    def __init__(self):
        super().__init__("video_recorder_node")

        # Parameters
        self.declare_parameter("input_topic", "/camera/image_raw")
        self.declare_parameter("output_path", "recorded_output.mp4")
        self.declare_parameter("fps", 15.0)
        self.declare_parameter("force_color", False)  # useful for mono8 mask if needed

        self.input_topic = self.get_parameter("input_topic").value
        self.output_path = self.get_parameter("output_path").value
        self.fps = float(self.get_parameter("fps").value)
        self.force_color = bool(self.get_parameter("force_color").value)

        self.bridge = CvBridge()
        self.writer = None
        self.frame_count = 0

        self.subscription = self.create_subscription(
            Image,
            self.input_topic,
            self.image_callback,
            10
        )

        self.get_logger().info(f"Recording topic: {self.input_topic}")
        self.get_logger().info(f"Saving to: {self.output_path}")
        self.get_logger().info(f"Target FPS: {self.fps}")

    def image_callback(self, msg: Image):
        try:
            # Handle both mono8 and bgr8 automatically
            if msg.encoding == "mono8":
                frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="mono8")
            else:
                frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().error(f"cv_bridge conversion failed: {e}")
            return

        if frame is None:
            return

        # Optionally convert mono to BGR if you want a color-coded mp4 path
        if len(frame.shape) == 2:
            is_color = False
            out_frame = frame

            if self.force_color:
                out_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                is_color = True
        else:
            is_color = True
            out_frame = frame

        # Lazy-init writer on first frame
        if self.writer is None:
            height, width = out_frame.shape[:2]

            # mp4v is usually the safest simple choice
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")

            self.writer = cv2.VideoWriter(
                self.output_path,
                fourcc,
                self.fps,
                (width, height),
                isColor=is_color
            )

            if not self.writer.isOpened():
                self.get_logger().error("Failed to open VideoWriter.")
                self.writer = None
                return

            self.get_logger().info(f"VideoWriter initialized: {width}x{height}, color={is_color}")

        self.writer.write(out_frame)
        self.frame_count += 1

        if self.frame_count % 30 == 0:
            self.get_logger().info(f"Recorded {self.frame_count} frames")

    def destroy_node(self):
        if self.writer is not None:
            self.writer.release()
            self.get_logger().info(
                f"Saved video: {os.path.abspath(self.output_path)} ({self.frame_count} frames)"
            )
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = VideoRecorderNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()