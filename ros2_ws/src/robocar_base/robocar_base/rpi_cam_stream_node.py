#!/usr/bin/env python3

import subprocess
import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class RpiCamStreamNode(Node):
    def __init__(self):
        super().__init__("rpicam_stream_node")

        # Parameters
        self.declare_parameter("width", 640)
        self.declare_parameter("height", 480)
        self.declare_parameter("fps", 15)
        self.declare_parameter("frame_id", "camera_frame")
        self.declare_parameter("topic", "/camera/image_raw")

        self.width = self.get_parameter("width").value
        self.height = self.get_parameter("height").value
        self.fps = self.get_parameter("fps").value
        self.frame_id = self.get_parameter("frame_id").value
        self.topic = self.get_parameter("topic").value

        self.publisher_ = self.create_publisher(Image, self.topic, 10)
        self.bridge = CvBridge()

        self.proc = None
        self.buffer = b""

        self.start_camera()

        timer_period = 1.0 / float(self.fps)
        self.timer = self.create_timer(timer_period, self.read_and_publish)

        self.get_logger().info(
            f"Streaming camera to {self.topic} at {self.width}x{self.height} @ {self.fps} FPS"
        )

    def start_camera(self):
        cmd = [
            "rpicam-vid",
            "-t", "0",
            "--codec", "mjpeg",
            "--width", str(self.width),
            "--height", str(self.height),
            "--framerate", str(self.fps),
            "--nopreview",
            "-o", "-"
        ]

        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0
        )

    def read_and_publish(self):
        if self.proc is None or self.proc.stdout is None:
            return

        try:
            chunk = self.proc.stdout.read(4096)
            if not chunk:
                self.get_logger().warn("No camera data received.")
                return

            self.buffer += chunk

            start = self.buffer.find(b"\xff\xd8")
            end = self.buffer.find(b"\xff\xd9")

            if start != -1 and end != -1 and end > start:
                jpg = self.buffer[start:end + 2]
                self.buffer = self.buffer[end + 2:]

                frame = cv2.imdecode(
                    np.frombuffer(jpg, dtype=np.uint8),
                    cv2.IMREAD_COLOR
                )

                if frame is None:
                    return

                msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.header.frame_id = self.frame_id
                self.publisher_.publish(msg)

        except Exception as e:
            self.get_logger().error(f"Camera stream error: {e}")

    def destroy_node(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass

        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RpiCamStreamNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()