#!/usr/bin/env python3
import sys
from pathlib import Path
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


class CmdVelToRoboCar(Node):
    """
    /cmd_vel → DC motors (throttle) + steering servo

    Convention from behaviour_manager:
      linear.x > 0, angular.z = value  → Ackermann: both motors forward, servo steers
      linear.x = 0, angular.z ≠ 0     → Tank turn: differential motors, servo centered
      linear.x = 0, angular.z = 0     → Stop
    """

    def __init__(self):
        super().__init__("cmd_vel_to_robocar")

        # ---------------- Params ----------------
        # Motor pins
        self.declare_parameter("left_pwm", "P13")
        self.declare_parameter("left_dir", "D4")
        self.declare_parameter("right_pwm", "P12")
        self.declare_parameter("right_dir", "D5")

        # Steering servo
        self.declare_parameter("steer_servo_channel", 0)
        self.declare_parameter("steer_center_deg", 0.0)
        self.declare_parameter("steer_max_deg", 25.0)
        self.declare_parameter("invert_steer", False)

        # Direction fixes
        self.declare_parameter("invert_left", False)
        self.declare_parameter("invert_right", True)

        # Scaling
        self.declare_parameter("throttle_gain", 350.0)   # motor % per m/s
        self.declare_parameter("motor_deadband", 0.0)
        self.declare_parameter("timeout_s", 0.5)

        # ---------------- Load params ----------------
        self.left_pwm = self.get_parameter("left_pwm").value
        self.left_dir = self.get_parameter("left_dir").value
        self.right_pwm = self.get_parameter("right_pwm").value
        self.right_dir = self.get_parameter("right_dir").value

        self.invert_left = self.get_parameter("invert_left").value
        self.invert_right = self.get_parameter("invert_right").value

        self.throttle_gain = float(self.get_parameter("throttle_gain").value)
        self.motor_deadband = float(self.get_parameter("motor_deadband").value)
        self.timeout_s = float(self.get_parameter("timeout_s").value)

        self.steer_ch = int(self.get_parameter("steer_servo_channel").value)
        self.steer_center = float(self.get_parameter("steer_center_deg").value)
        self.steer_max = float(self.get_parameter("steer_max_deg").value)
        self.invert_steer = bool(self.get_parameter("invert_steer").value)

        self.last_cmd_time = self.get_clock().now()

        # ---------------- Hardware init ----------------
        self._init_hw_or_die()

        # ROS
        self.sub = self.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)
        self.timer = self.create_timer(0.05, self.on_timer)

        self.get_logger().info("cmd_vel → motors + steering servo ready")

    # -------------------------------------------------
    def _init_hw_or_die(self):
        try:
            from robot_hat.motor import Motor
            from robot_hat.pwm import PWM
            from robot_hat.pin import Pin
            from robot_hat.servo import Servo

            self.left_motor = Motor(PWM(self.left_pwm), Pin(self.left_dir))
            self.right_motor = Motor(PWM(self.right_pwm), Pin(self.right_dir))
            self.steer_servo = Servo(self.steer_ch)

            self.left_motor.speed(0)
            self.right_motor.speed(0)
            self.steer_servo.angle(self.steer_center)

            self.get_logger().info("robot_hat motors + servo initialized")
        except Exception as e:
            raise RuntimeError(f"robot_hat init failed: {e}")

    # -------------------------------------------------
    def set_motors(self, pct):
        pct = clamp(pct, -100.0, 100.0)

        if abs(pct) < self.motor_deadband:
            pct = 0.0

        l = -pct if self.invert_left else pct
        r = -pct if self.invert_right else pct

        self.left_motor.speed(int(l))
        self.right_motor.speed(int(r))

    def set_independent_motors(self, left_pct, right_pct):
        """Set left and right motors independently (for tank turns)."""
        left_pct = clamp(left_pct, -100.0, 100.0)
        right_pct = clamp(right_pct, -100.0, 100.0)

        l = -left_pct if self.invert_left else left_pct
        r = -right_pct if self.invert_right else right_pct

        self.left_motor.speed(int(l))
        self.right_motor.speed(int(r))

    def set_steering(self, steer_norm):
        """
        steer_norm ∈ [-1, 1] → servo angle
        """
        steer_norm = clamp(steer_norm, -1.0, 1.0)
        if self.invert_steer:
            steer_norm *= -1.0

        angle = self.steer_center + steer_norm * self.steer_max
        self.steer_servo.angle(angle)

    # -------------------------------------------------
    def on_cmd_vel(self, msg: Twist):
        self.last_cmd_time = self.get_clock().now()

        v = float(msg.linear.x)
        w = float(msg.angular.z)

        if v > 0.0:
            # Ackermann: both motors forward, servo steers
            throttle_pct = self.throttle_gain * v
            self.set_motors(throttle_pct)
            self.set_steering(clamp(w, -1.0, 1.0))

        elif w != 0.0:
            # Tank turn: differential motors, servo centered
            turn_pct = self.throttle_gain * abs(w)
            if w > 0:
                self.set_independent_motors(-turn_pct, turn_pct)
            else:
                self.set_independent_motors(turn_pct, -turn_pct)
            self.set_steering(0.0)

        else:
            # Stop
            self.set_motors(0.0)
            self.set_steering(0.0)

    def on_timer(self):
        age = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9
        if age > self.timeout_s:
            self.set_motors(0.0)
            self.set_steering(0.0)


def main():
    rclpy.init()
    node = CmdVelToRoboCar()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.set_motors(0.0)
        node.set_steering(0.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
