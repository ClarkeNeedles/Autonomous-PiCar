#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, String


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


class CmdVelToRoboCar(Node):
    """
    /cmd_vel → DC motors (throttle) + steering servo

    Convention from behaviour_manager:
      linear.x > 0, angular.z = value  -> Ackermann: both motors forward, servo steers
      linear.x = 0, angular.z != 0     -> Tank turn: differential motors, servo centered
      linear.x = 0, angular.z = 0      -> Stop
    """

    def __init__(self):
        super().__init__("cmd_vel_to_robocar")

        # ---------------- Params ----------------
        self.declare_parameter("left_pwm", "P13")
        self.declare_parameter("left_dir", "D4")
        self.declare_parameter("right_pwm", "P12")
        self.declare_parameter("right_dir", "D5")

        self.declare_parameter("steer_servo_channel", 2)
        self.declare_parameter("steer_center_deg", -8.0)
        self.declare_parameter("steer_max_deg", 35.0)
        self.declare_parameter("invert_steer", False)

        self.declare_parameter("invert_left", False)
        self.declare_parameter("invert_right", True)

        self.declare_parameter("throttle_gain", 350.0)
        self.declare_parameter("motor_deadband", 0.0)
        self.declare_parameter("timeout_s", 0.5)

        # ---------------- Load params ----------------
        self.left_pwm = self.get_parameter("left_pwm").value
        self.left_dir = self.get_parameter("left_dir").value
        self.right_pwm = self.get_parameter("right_pwm").value
        self.right_dir = self.get_parameter("right_dir").value

        self.invert_left = bool(self.get_parameter("invert_left").value)
        self.invert_right = bool(self.get_parameter("invert_right").value)

        self.throttle_gain = float(self.get_parameter("throttle_gain").value)
        self.motor_deadband = float(self.get_parameter("motor_deadband").value)
        self.timeout_s = float(self.get_parameter("timeout_s").value)

        self.steer_ch = int(self.get_parameter("steer_servo_channel").value)
        self.steer_center = float(self.get_parameter("steer_center_deg").value)
        self.steer_max = float(self.get_parameter("steer_max_deg").value)
        self.invert_steer = bool(self.get_parameter("invert_steer").value)

        # ---------------- State ----------------
        self.last_cmd_time = self.get_clock().now()
        self.tank_steer = False

        self.left_signal_on = False
        self.right_signal_on = False
        self.brake_lights_on = False

        self.turn_signal_state = "NONE"
        self.hazard_active = False
        self.blink_on = False

        self.last_linear_cmd = 0.0
        self.last_angular_cmd = 0.0

        # ---------------- Hardware init ----------------
        self._init_hw_or_die()

        # ---------------- ROS ----------------
        self.sub = self.create_subscription(Twist, "/cmd_vel", self.on_cmd_vel, 10)
        self.sub_tank = self.create_subscription(Bool, "/tank_steer", self.on_tank_steer, 10)
        self.turn_signal_sub = self.create_subscription(
            String, "/turn_signal_cmd", self.on_turn_signal, 10
        )
        self.ultrasonic_sub = self.create_subscription(
            Bool, "/ultrasonic/detected", self.ultrasonic_callback, 10
        )

        self.timer = self.create_timer(0.05, self.on_timer)
        self.blink_timer = self.create_timer(0.25, self.blink_timer_callback)

        self.get_logger().info("cmd_vel -> motors + steering servo ready")

    def _init_hw_or_die(self):
        try:
            from robot_hat.motor import Motor
            from robot_hat.pwm import PWM
            from robot_hat.pin import Pin
            from robot_hat.servo import Servo

            self.left_motor = Motor(PWM(self.left_pwm), Pin(self.left_dir))
            self.right_motor = Motor(PWM(self.right_pwm), Pin(self.right_dir))
            self.steer_servo = Servo(self.steer_ch)

            # LEDs
            self.left_led = PWM("P8")
            self.right_led = PWM("P9")
            self.stop_led_1 = PWM("P10")
            self.stop_led_2 = PWM("P11")

            self.left_motor.speed(0)
            self.right_motor.speed(0)
            self.steer_servo.angle(self.steer_center)

            self._set_left_signal(False)
            self._set_right_signal(False)
            self._set_brake_lights(False)

            self.get_logger().info("robot_hat motors + servo initialized")
        except Exception as e:
            raise RuntimeError(f"robot_hat init failed: {e}")

    def _set_pwm_led(self, led, on: bool):
        led.pulse_width_percent(100 if on else 0)

    def _set_left_signal(self, on: bool):
        if self.left_signal_on == on:
            return
        self.left_signal_on = on
        self._set_pwm_led(self.left_led, on)

    def _set_right_signal(self, on: bool):
        if self.right_signal_on == on:
            return
        self.right_signal_on = on
        self._set_pwm_led(self.right_led, on)

    def _set_brake_lights(self, on: bool):
        if self.brake_lights_on == on:
            return
        self.brake_lights_on = on
        self._set_pwm_led(self.stop_led_1, on)
        self._set_pwm_led(self.stop_led_2, on)
        self.get_logger().info(f"Brake lights: {'ON' if on else 'OFF'}")

    def set_motors(self, pct):
        pct = clamp(pct, -100.0, 100.0)

        if abs(pct) < self.motor_deadband:
            pct = 0.0

        l = -pct if self.invert_left else pct
        r = -pct if self.invert_right else pct

        self.left_motor.speed(int(l))
        self.right_motor.speed(int(r))

    def set_independent_motors(self, left_pct, right_pct):
        left_pct = clamp(left_pct, -100.0, 100.0)
        right_pct = clamp(right_pct, -100.0, 100.0)

        if abs(left_pct) < self.motor_deadband:
            left_pct = 0.0
        if abs(right_pct) < self.motor_deadband:
            right_pct = 0.0

        l = -left_pct if self.invert_left else left_pct
        r = -right_pct if self.invert_right else right_pct

        self.left_motor.speed(int(l))
        self.right_motor.speed(int(r))

    def set_steering(self, steer_norm):
        steer_norm = clamp(steer_norm, -1.0, 1.0)
        if self.invert_steer:
            steer_norm *= -1.0

        angle = self.steer_center + steer_norm * self.steer_max
        self.steer_servo.angle(angle)

    def on_tank_steer(self, msg: Bool):
        self.tank_steer = msg.data
        self.get_logger().info(f"Tank steer: {'ON' if self.tank_steer else 'OFF'}")

    def on_turn_signal(self, msg: String):
        self.turn_signal_state = msg.data.strip().upper()

    def ultrasonic_callback(self, msg: Bool):
        self.hazard_active = msg.data

    def blink_timer_callback(self):
        self.blink_on = not self.blink_on

        # Hazard override: both blink
        if self.hazard_active:
            self._set_left_signal(self.blink_on)
            self._set_right_signal(self.blink_on)
            return

        # Normal turn signal behavior
        if self.turn_signal_state == "LEFT":
            self._set_left_signal(self.blink_on)
            self._set_right_signal(False)
        elif self.turn_signal_state == "RIGHT":
            self._set_left_signal(False)
            self._set_right_signal(self.blink_on)
        else:
            self._set_left_signal(False)
            self._set_right_signal(False)

    def on_cmd_vel(self, msg: Twist):
        self.last_cmd_time = self.get_clock().now()

        v = float(msg.linear.x)
        w = float(msg.angular.z)

        self.last_linear_cmd = v
        self.last_angular_cmd = w

        if self.tank_steer:
            turn_pct = self.throttle_gain * abs(w)

            if w > 0:
                self.set_independent_motors(-turn_pct, turn_pct)
            elif w < 0:
                self.set_independent_motors(turn_pct, -turn_pct)
            else:
                self.set_motors(0.0)

            self.set_steering(0.0)
        else:
            throttle_pct = self.throttle_gain * v
            self.set_motors(throttle_pct)
            self.set_steering(w)

        moving = abs(v) > 1e-3 or abs(w) > 1e-3
        self._set_brake_lights(not moving)

    def on_timer(self):
        age = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9

        if age > self.timeout_s:
            self.set_motors(0.0)
            self.set_steering(0.0)
            self.last_linear_cmd = 0.0
            self.last_angular_cmd = 0.0
            self._set_brake_lights(True)

            # Do not force turn signals off here.
            # Let blink_timer_callback() handle turn signals / hazards.

    def shutdown_outputs(self):
        self.set_motors(0.0)
        self.set_steering(0.0)
        self._set_brake_lights(True)
        self._set_left_signal(False)
        self._set_right_signal(False)


def main():
    rclpy.init()
    node = CmdVelToRoboCar()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown_outputs()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()