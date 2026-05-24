#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from robot_hat import ADC

class GrayscaleCalibration(Node):
    def __init__(self):
        super().__init__("grayscale_calib")

        # -------- Parameters --------
        self.declare_parameter("left_channel", "A0")
        self.declare_parameter("center_channel", "A1")
        self.declare_parameter("right_channel", "A2")

        self.left_ch = self.get_parameter("left_channel").value
        self.center_ch = self.get_parameter("center_channel").value
        self.right_ch = self.get_parameter("right_channel").value

        # -------- Hardware --------
        self.left_adc = ADC(self.left_ch)
        self.center_adc = ADC(self.center_ch)
        self.right_adc = ADC(self.right_ch)

        # -------- Timer --------
        self.timer = self.create_timer(0.1, self.read_and_print)

        self.get_logger().info("Grayscale calibration node started")
        self.get_logger().info("Move sensors over floor and line to record values")

    def read_and_print(self):
        l = self.left_adc.read()
        c = self.center_adc.read()
        r = self.right_adc.read()

        print(f"L: {l:4d} | C: {c:4d} | R: {r:4d}")

def main():
    rclpy.init()
    node = GrayscaleCalibration()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()