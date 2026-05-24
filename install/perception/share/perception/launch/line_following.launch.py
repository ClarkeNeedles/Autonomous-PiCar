#!/usr/bin/env python3
import os
from pathlib import Path

from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable
from launch_ros.actions import Node


def _resolve_robot_hat_path():
    env_path = os.environ.get("ROBOT_HAT_PATH")
    candidates = []
    if env_path:
        candidates.append(Path(env_path).expanduser())

    home = Path.home()
    candidates.extend([
        home / "elec-392-project-blekinge-12" / "ros2_ws" / "robot-hat",
        home / "ros2_ws" / "robot-hat",
    ])

    for candidate in candidates:
        if candidate.is_dir():
            return str(candidate)

    return None


def generate_launch_description():
    actions = []
    robot_hat_path = _resolve_robot_hat_path()

    if robot_hat_path:
        actions.append(SetEnvironmentVariable(
            "PYTHONPATH",
            robot_hat_path + os.pathsep + os.environ.get("PYTHONPATH", "")
        ))

    actions.extend([
        Node(
            package="perception",
            executable="segmentation_node",
            name="segmentation_node",
            output="screen",
        ),
        Node(
            package="perception",
            executable="autonomy_node",
            name="autonomy_node",
            output="screen",
        ),
        Node(
            package="hardware_pkg",
            executable="cmd_vel_to_robocar",
            name="cmd_vel_to_robocar",
            output="screen",
        ),
    ])

    return LaunchDescription(actions)
