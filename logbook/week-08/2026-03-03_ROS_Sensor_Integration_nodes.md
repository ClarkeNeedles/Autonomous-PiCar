---
title: "Initial Implementation of ROS Sensor Nodes"
date: 2026-03-03
week: 8
hours: 3
tags: [ROS2, sensors, implementation, integration]
contributors: [Ben, Clarke, Filip, Jimmy]
author: Ben Malvern
status: Completed
---

# Daily Logbook Entry Template

> **Instructions**: This is an example of a logbook template that describes work done on your project in a systematic manner. Copy this template to create your daily entries. Save as: `logbook/week-XX/YYYY-MM-DD_brief-description.md`

## Objectives

What did you plan to accomplish in this session?

- Implement the basic structure for the greyscale + ultrasound ROS sensor nodes
- Establish topic publishers for camera and other sensor inputs
- Verify that sensor nodes can publish data correctly within the ROS system

## Detailed Work Log

### Session 1: Sensor Node Creation (13:00 - 14:30)

**Members Present**: [Ben, Clarke, Filip, Jimmy]

**Description**:  
Created the initial ROS node files responsible for publishing sensor data used by the autonomy stack. The goal was to establish a working structure for sensor nodes so that downstream perception and localization modules could subscribe to these topics.

**Materials/Tools Used**:

- ROS2 workspace
- Python and c++ ROS2 node templates
- Project architecture diagram
- VS Code

**Process/Steps**:

1. Created new sensor node scripts within the ROS workspace
2. Implemented basic ROS node initialization
3. Defined publishers for relevant sensor topics
4. Verified node compilation and execution
5. Confirmed topics appeared in the ROS topic list

**Documentation**:

### Session 2: Topic Publishing Verification (14:30 - 16:00)

**Members Present**: [Ben, Clarke, Filip, Jimmy]

**Description**:  
Tested the basic sensor nodes (greyscale + ultrasound) to ensure topics were publishing correctly and could be detected by other nodes within the system.

## Results & Data

### Measurements/Observations

| Parameter        | Expected                         | Measured  | Pass/Fail | Notes                                 |
| ---------------- | -------------------------------- | --------- | --------- | ------------------------------------- |
| Node startup     | Sensor nodes launch successfully | Confirmed | Pass      | Nodes initialize correctly            |
| Topic publishing | Topics visible in ROS            | Confirmed | Pass      | Topics detected via `ros2 topic list` |
| Message flow     | Basic message data transmitted   | Confirmed | Pass      | Ready for integration                 |

### Code Snippets

Example basic ROS2 sensor node structure (excludes hardware interfacing drivers):

```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class SensorNode(Node):

    def __init__(self):
        super().__init__('sensor_node')
        self.publisher = self.create_publisher(String, 'sensor_data', 10)

def main():
    rclpy.init()
    node = SensorNode()
    rclpy.spin(node)
```
