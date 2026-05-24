import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from robot_hat.modules import Ultrasonic
from robot_hat.pin import Pin


class UltrasonicNode(Node):
    def __init__(self):
        super().__init__("ultrasonic_node")

        # Parameters
        self.declare_parameter("trigger_pin", "D2")
        self.declare_parameter("echo_pin", "D3")
        self.declare_parameter("min_range", 2.0) # cm
        self.declare_parameter("max_range", 400.0) # cm
        self.declare_parameter("frame_id", "ultrasonic_link")
        self.declare_parameter("publish_hz", 10.0)
        self.declare_parameter("field_of_view", 0.5)

        # Detection parameters
        self.declare_parameter("stop_threshold_cm", 15.0)
        self.declare_parameter("min_consecutive_reads", 5)

        # Load params
        trig_name = self.get_parameter("trigger_pin").value
        echo_name = self.get_parameter("echo_pin").value
        self.min_range = float(self.get_parameter("min_range").value)
        self.max_range = float(self.get_parameter("max_range").value)
        self.frame_id = self.get_parameter("frame_id").value
        self.publish_hz = float(self.get_parameter("publish_hz").value)
        self.field_of_view = float(self.get_parameter("field_of_view").value)

        self.stop_threshold_cm = float(self.get_parameter("stop_threshold_cm").value)
        self.stop_min_cm = self.min_range          # use sensor min_range as lower bound
        self.stop_max_cm = self.stop_threshold_cm  # anything closer than threshold triggers stop
        self.min_consecutive_reads = int(self.get_parameter("min_consecutive_reads").value)

        # Detection state
        self.close_count = 0
        self.obstacle_detected = False
        self.prev = None

        # Hardware setup
        try:
            trig = Pin(trig_name, Pin.OUT)
            echo = Pin(echo_name, mode=Pin.IN, pull=Pin.PULL_DOWN)
            self.sensor = Ultrasonic(trig, echo)
        except Exception as e:
            self.get_logger().error(f"Failed to initialize ultrasonic sensor: {e}")
            raise

        # Publishers
        self.detected_pub = self.create_publisher(Bool, "/ultrasonic/detected", 10)

        # Timer
        period = 1.0 / self.publish_hz if self.publish_hz > 0 else 0.1
        self.timer = self.create_timer(period, self.update)

        self.get_logger().info("Ultrasonic node started")

    def update_detection(self, distance_cm: float) -> bool:
        """Update detection state based on consecutive close readings."""
        in_stop_window = self.stop_min_cm <= distance_cm <= self.stop_max_cm

        if in_stop_window:
            self.close_count += 1

            message = (
                f"[ultrasonic] close reading: {distance_cm:.2f} cm "
                f"({self.close_count}/{self.min_consecutive_reads})"
            )
            print(message, flush=True)
            self.get_logger().info(message)

            if self.close_count >= self.min_consecutive_reads:
                if not self.obstacle_detected:
                    detected_message = (
                        f"[ultrasonic] OBSTACLE DETECTED within {self.stop_threshold_cm:.2f} cm "
                        f"for {self.min_consecutive_reads} consecutive readings!"
                    )
                    print(detected_message, flush=True)
                    self.get_logger().warn(detected_message)
                self.obstacle_detected = True
        else:
            if self.obstacle_detected or self.close_count > 0:
                cleared_message = f"[ultrasonic] cleared at {distance_cm:.2f} cm"
                print(cleared_message, flush=True)
                self.get_logger().info(cleared_message)
            self.close_count = 0
            self.obstacle_detected = False

        return self.obstacle_detected

    def update(self):
        if not rclpy.ok():
            return
        # Read distance in cm
        try:
            d = float(self.sensor.read())
        except Exception as e:
            self.get_logger().warn(f"Ultrasonic read failed: {e}")
            return None

        if d is None or d < 0:
            return None

        # Clamp to valid configured limits
        if d < self.min_range:
            d = self.min_range
        elif d > self.max_range:
            d = self.max_range

        # Simple smoothing
        if self.prev is None:
            filtered = d
        else:
            filtered = 0.7 * self.prev + 0.3 * d

        self.prev = filtered

        # Update detection logic using filtered value
        detected = self.update_detection(filtered)

        # Publish Bool detection message
        detected_msg = Bool()
        detected_msg.data = detected
        self.detected_pub.publish(detected_msg)

        self.get_logger().info(
            f"Ultrasonic debug | distance: {filtered:.2f} cm | in_range: {self.stop_min_cm <= filtered <= self.stop_max_cm} | detected: {detected}",
            throttle_duration_sec=2.0,
        )

    def destroy_node(self):
        try:
            if hasattr(self, "sensor"):
                if hasattr(self.sensor, "trig"):
                    self.sensor.trig.close()
                if hasattr(self.sensor, "echo"):
                    self.sensor.echo.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UltrasonicNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
