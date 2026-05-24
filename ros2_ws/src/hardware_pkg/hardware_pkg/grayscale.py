import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from robot_hat import ADC
from modules import Grayscale_Module

class GrayscaleNode(Node):
    def __init__(self):
        super().__init__("grayscale_node")

        # Sensor channels
        self.declare_parameter("left_channel", "A0")
        self.declare_parameter("center_channel", "A1")
        self.declare_parameter("right_channel", "A2")

        # Calibration constants
        self.declare_parameter("left_floor", 93.0)
        self.declare_parameter("left_line", 1100.0)
        self.declare_parameter("center_floor", 84.0)
        self.declare_parameter("center_line", 1402.0)
        self.declare_parameter("right_floor", 100.0)
        self.declare_parameter("right_line", 1458.0)

        # Timer rate
        self.declare_parameter("publish_hz", 20.0)

        # Optional debug logging
        self.declare_parameter("debug", False)

        # Load parameters
        self.left_channel = self.get_parameter("left_channel").value
        self.center_channel = self.get_parameter("center_channel").value
        self.right_channel = self.get_parameter("right_channel").value

        self.left_floor = float(self.get_parameter("left_floor").value)
        self.left_line = float(self.get_parameter("left_line").value)
        self.center_floor = float(self.get_parameter("center_floor").value)
        self.center_line = float(self.get_parameter("center_line").value)
        self.right_floor = float(self.get_parameter("right_floor").value)
        self.right_line = float(self.get_parameter("right_line").value)

        self.publish_hz = float(self.get_parameter("publish_hz").value)
        self.debug = bool(self.get_parameter("debug").value)

        # Hardware ADCs
        left_adc = ADC(self.left_channel)
        center_adc = ADC(self.center_channel)
        right_adc = ADC(self.right_channel)

        # Grayscale module
        self.grayscale = Grayscale_Module(left_adc, center_adc, right_adc)

        # Publishers
        self.offset_pub = self.create_publisher(
            Float32, "/grayscale_lane/lateral_offset", 10
        )
        self.conf_pub = self.create_publisher(
            Float32, "/grayscale_lane/confidence", 10
        )

        # Timer
        period = 1.0 / self.publish_hz if self.publish_hz > 0.0 else 0.05
        self.timer = self.create_timer(period, self.update)

        self.get_logger().info("grayscale_node started")
        self.get_logger().info(
            f"Using channels L={self.left_channel}, C={self.center_channel}, R={self.right_channel}"
        )

    def normalize_sensor(self, reading, floor_val, line_val):
        """
        Convert raw ADC reading to line strength in [0, 1].
        Floor is low and line is high.
        """
        if abs(line_val - floor_val) < 1e-6:
            return 0.0

        strength = (reading - floor_val) / (line_val - floor_val)

        if strength < 0.0:
            return 0.0
        elif strength > 1.0:
            return 1.0
        else:
            return strength

    def update(self):
        # Read raw values from Grayscale_Module
        raw_vals = self.grayscale.read()
        raw_l = float(raw_vals[0])
        raw_c = float(raw_vals[1])
        raw_r = float(raw_vals[2])

        # Normalize to strengths [0, 1]
        l = self.normalize_sensor(raw_l, self.left_floor, self.left_line)
        c = self.normalize_sensor(raw_c, self.center_floor, self.center_line)
        r = self.normalize_sensor(raw_r, self.right_floor, self.right_line)

        # Weighted offset
        # left = -1, center = 0, right = +1
        total = l + c + r

        if total < 1e-6:
            offset = 0.0
            confidence = 0.0
        else:
            offset = (-1.0 * l + 1.0 * r) / total
            confidence = max(l, c, r)

        # Publish
        self.offset_pub.publish(Float32(data=float(offset)))
        self.conf_pub.publish(Float32(data=float(confidence)))

        if self.debug:
            self.get_logger().info(
                f"raw L/C/R = ({raw_l:.0f}, {raw_c:.0f}, {raw_r:.0f}) | "
                f"norm = ({l:.2f}, {c:.2f}, {r:.2f}) | "
                f"offset = {offset:.2f}, conf = {confidence:.2f}"
            )

def main(args=None):
    rclpy.init(args=args)
    node = GrayscaleNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()