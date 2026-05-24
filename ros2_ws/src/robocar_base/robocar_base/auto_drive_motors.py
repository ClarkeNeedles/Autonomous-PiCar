#!/usr/bin/env python3
import signal

import rclpy
from rclpy.node import Node


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class AutoDriveMotors(Node):
    """
    Drives robot_hat motors automatically (no /cmd_vel needed).

    Pattern:
      - forward for forward_s seconds
      - stop for stop_s seconds
      - reverse for reverse_s seconds
      - stop for stop_s seconds
      - repeat
    """

    def __init__(self):
        super().__init__("auto_drive_motors")

        # ----- Params -----
        self.declare_parameter("left_pwm", "P13")
        self.declare_parameter("left_dir", "D4")
        self.declare_parameter("right_pwm", "P12")
        self.declare_parameter("right_dir", "D5")

        self.declare_parameter("invert_left", False)
        self.declare_parameter("invert_right", False)

        self.declare_parameter("speed_pct", 25.0)   # motor percent
        self.declare_parameter("turn_pct", 0.0)     # differential mix, percent

        self.declare_parameter("forward_s", 2.0)
        self.declare_parameter("reverse_s", 2.0)
        self.declare_parameter("stop_s", 1.0)

        self.declare_parameter("motor_deadband", 3.0)

        # ----- Load params -----
        self.left_pwm = str(self.get_parameter("left_pwm").value)
        self.left_dir = str(self.get_parameter("left_dir").value)
        self.right_pwm = str(self.get_parameter("right_pwm").value)
        self.right_dir = str(self.get_parameter("right_dir").value)

        self.invert_left = bool(self.get_parameter("invert_left").value)
        self.invert_right = bool(self.get_parameter("invert_right").value)

        self.speed_pct = float(self.get_parameter("speed_pct").value)
        self.turn_pct = float(self.get_parameter("turn_pct").value)

        self.forward_s = float(self.get_parameter("forward_s").value)
        self.reverse_s = float(self.get_parameter("reverse_s").value)
        self.stop_s = float(self.get_parameter("stop_s").value)

        self.motor_deadband = float(self.get_parameter("motor_deadband").value)

        # ----- Hardware init -----
        self._init_hw_or_die()

        # ----- State machine -----
        self.state = "forward"  # forward -> stop1 -> reverse -> stop2 -> repeat
        self.state_start = self.get_clock().now()

        # Timer tick
        self.timer = self.create_timer(0.05, self.on_timer)

        self.get_logger().info(
            f"AutoDrive started. speed_pct={self.speed_pct} turn_pct={self.turn_pct} "
            f"forward_s={self.forward_s} reverse_s={self.reverse_s} stop_s={self.stop_s}"
        )

    def _init_hw_or_die(self) -> None:
        """
        Hard-fail if robot_hat isn't available or motors can't initialize.
        This prevents silent "node runs but motors never move".
        """
        try:
            import robot_hat
            self.get_logger().info(f"robot_hat imported from: {robot_hat.__file__}")

            from robot_hat import Motor, PWM, Pin

            self.left_motor = Motor(PWM(self.left_pwm), Pin(self.left_dir))
            self.right_motor = Motor(PWM(self.right_pwm), Pin(self.right_dir))

            # Safe initial state
            self.left_motor.speed(0)
            self.right_motor.speed(0)

            self.get_logger().info("robot_hat motors initialized OK.")
        except Exception as e:
            raise RuntimeError(f"robot_hat init failed: {e}")

    def set_motor_speeds(self, left_pct: float, right_pct: float):
        left_pct = clamp(left_pct, -100.0, 100.0)
        right_pct = clamp(right_pct, -100.0, 100.0)

        if abs(left_pct) < self.motor_deadband:
            left_pct = 0.0
        if abs(right_pct) < self.motor_deadband:
            right_pct = 0.0

        if self.invert_left:
            left_pct *= -1.0
        if self.invert_right:
            right_pct *= -1.0

        try:
            self.left_motor.speed(int(left_pct))
            self.right_motor.speed(int(right_pct))
        except Exception as e:
            self.get_logger().error(f"Motor speed set failed: {e}")

    def _elapsed(self) -> float:
        return (self.get_clock().now() - self.state_start).nanoseconds / 1e9

    def on_timer(self):
        if self.state == "forward":
            self.set_motor_speeds(self.speed_pct - self.turn_pct, self.speed_pct + self.turn_pct)
            if self._elapsed() >= self.forward_s:
                self.state = "stop1"
                self.state_start = self.get_clock().now()

        elif self.state == "stop1":
            self.set_motor_speeds(0.0, 0.0)
            if self._elapsed() >= self.stop_s:
                self.state = "reverse"
                self.state_start = self.get_clock().now()

        elif self.state == "reverse":
            self.set_motor_speeds(-self.speed_pct + self.turn_pct, -self.speed_pct - self.turn_pct)
            if self._elapsed() >= self.reverse_s:
                self.state = "stop2"
                self.state_start = self.get_clock().now()

        elif self.state == "stop2":
            self.set_motor_speeds(0.0, 0.0)
            if self._elapsed() >= self.stop_s:
                self.state = "forward"
                self.state_start = self.get_clock().now()

        else:
            self.set_motor_speeds(0.0, 0.0)
            self.state = "forward"
            self.state_start = self.get_clock().now()

    def destroy_node(self):
        try:
            self.set_motor_speeds(0.0, 0.0)
        except Exception:
            pass
        super().destroy_node()


def main():
    rclpy.init()
    node = AutoDriveMotors()

    def handle_shutdown_signal(_signum, _frame):
        rclpy.try_shutdown()

    previous_sigint = signal.getsignal(signal.SIGINT)
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)
        try:
            node.set_motor_speeds(0.0, 0.0)
        except Exception:
            pass
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
