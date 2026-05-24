#!/bin/bash
# Kill all ROS nodes, camera processes, and release held hardware resources.

echo "Stopping ROS nodes..."
pkill -f "ros2 run"         2>/dev/null
pkill -f autonomy_node      2>/dev/null
pkill -f segmentation_node  2>/dev/null
pkill -f cmd_vel_to_robocar 2>/dev/null
pkill -f behavior_manager   2>/dev/null
pkill -f ultrasonic         2>/dev/null
pkill -f map_planner        2>/dev/null
pkill -f lane_follow        2>/dev/null

echo "Stopping camera..."
pkill -f rpicam-vid         2>/dev/null
pkill -f libcamera          2>/dev/null

echo "Stopping ROS daemon..."
ros2 daemon stop            2>/dev/null

# Wait for camera to fully release
sleep 2

echo "Done. All resources cleared."
