from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package="robocar_base",
            executable="cmd_vel_to_robocar",
            name="cmd_vel_to_robocar",
            output="screen",
            parameters=[
                {"wheel_base": 0.16},
                {"max_lin": 0.6},
                {"max_ang": 2.5},
                {"timeout_s": 0.5},

                # Your tested wiring
                {"left_pwm": "P13"},
                {"left_dir": "D4"},
                {"right_pwm": "P12"},
                {"right_dir": "D5"},

                # Flip whichever wheel is wrong
                {"invert_left": False},
                {"invert_right": True},   # try True if right wheel is backwards

                # Steering
                {"steer_servo_channel": 0},
                {"steer_center_deg": 0.0},
                {"steer_max_deg": 20.0},
                {"invert_steer": False},
            ],
        )
    ])
