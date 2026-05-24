---
title: "Sensor Nodes, Hardware Integration, and ROS2 Setup"
date: "2026-03-05"
time: "2:30 PM – 4:30 PM"
contributors: ["Ben Malvern", "Clarke Needles", "Jimmy Moutafis-Tymcio", "Filip Radenovic"]
tags: ["ROS2", "Sensors", "Hardware", "Perception", "Control"]
---

## Overview
This session focused on beginning development of sensor and hardware nodes, testing ROS2 node creation in both Python and C++, and continuing computer vision data collection. We also established a modular package structure, calibrated sensors, and debugged hardware issues.

Additionally, development was performed using a **Docker container**, allowing ROS2 nodes to be built and tested off the Raspberry Pi in a controlled environment before deployment.

---

## Agenda
- Start coding sensor nodes  
- Test ROS2 node creation (C++ and Python)  
- Collect additional video data for CV  
- Calibrate sensors and debug hardware  
- Establish ROS2 workflow and package structure  

---

## Discussion Summary

### Node Development & Package Structure
- Began creating ROS2 nodes for different subsystems of the RoboCar  
- Established structure of **one package per subsystem** (e.g., control, perception, hardware)  
- Standard node layout:
  ```
  package/package/node.py
  ```
- Nodes must be added to `setup.py` to be executable  

- Verified both:
  - Python nodes ✔  
  - C++ nodes ✔  

- Decision:
  - Use **Python nodes** for hardware interfacing (PiHat API simplifies sensor access)  
  - Use **C++ nodes** for compute-intensive logic (e.g., behavior manager)

---

### ROS2 Development Workflow

#### Build & Run
```bash
colcon build --packages-select my_package
source install/setup.bash
ros2 run my_package my_node
```

#### Topic Debugging
```bash
ros2 topic echo /your_topic_name
```

#### Package Creation

**C++ Package**
```bash
cd ~/elec-392-project-blekinge-12/ros2_ws/src
ros2 pkg create control_pkg --build-type ament_cmake --dependencies rclcpp std_msgs geometry_msgs nav_msgs sensor_msgs
```

**Python Package**
```bash
ros2 pkg create perception_pkg --build-type ament_python --dependencies rclpy std_msgs geometry_msgs nav_msgs sensor_msgs
```

---

### Development Environment (Docker)
- Used a **Docker container (ROS2 Humble base)** to develop and test nodes  
- Benefits:
  - Consistent environment across team members  
  - Faster iteration without relying on Raspberry Pi hardware  
  - Avoids dependency and OS-related issues on the Pi  
- Workflow:
  - Develop and build inside container  
  - Deploy to Pi once stable  

---

### Sensor Development & Calibration

#### Grayscale Sensor Calibration
- Collected raw readings to determine line vs floor values  
- Measured sensor strengths and offsets  

| Sensor | Line | Floor |
|--------|------|-------|
| L      | 1100 | 93    |
| C      | 1402 | 84    |
| R      | 1458 | 100   |

- Approach:
  - Compare relative values between sensors  
  - Use offsets to determine steering correction  

---

#### Ultrasonic Sensor
- Issue: inaccurate readings due to interference from metal bracket  
- Solution: applied electrical tape  
- Result:
  - Improved accuracy  
  - Offset approximately zero  

---

### Hardware Notes
- Speaker does **not work on Ubuntu Server**
  - Likely due to missing drivers  
  - Plan: switch to **3.5mm jack speaker**  

- PWM testing for brake lights:
  - Successfully implemented  
  - Brightness can scale with braking/acceleration  

---

### Computer Vision & Camera Decisions
- Continued collecting video data for training  
- Explored AI camera:
  - Blocked by firmware incompatibility with Ubuntu  
  - ROS2 requires Ubuntu-based system  

- Decision:
  - Use existing camera  
  - Run **object detection + lane segmentation on Coral accelerator**

---

### Behavior Manager Development (C++)
- Created C++ package for `behavior_manager` node  
- Purpose:
  - Subscribe to all system topics  
  - Control motors and high-level behavior  

- Reason for C++:
  - Higher performance for real-time control  

- Progress:
  - Established communication between Python and C++ nodes  
  - Implemented obstacle detection:
    - Detects objects within **15 cm**  
    - Outputs notification when triggered  

---

## Key Decisions
- Python for hardware nodes, C++ for compute-heavy nodes  
- Modular ROS2 architecture (one package per subsystem)  
- Use Docker for development instead of working directly on Pi  
- Continue using Coral accelerator for CV  
- Replace speaker with 3.5mm audio solution  

---

## Action Items
- [ ] Implement grayscale-based line following  
- [ ] Expand ultrasonic node to publish ROS2 messages  
- [ ] Continue collecting and labeling CV data  
- [ ] Integrate behavior manager with motor control  
- [ ] Test full system integration  
- [ ] Finalize audio solution compatible with Ubuntu  

---

## Notes
- Hardware issues require practical fixes (e.g., tape for ultrasonic sensor)  
- ROS2 architecture supports clean separation of concerns  
- Docker significantly improves development workflow and reliability  
- Initial inter-node communication between Python and C++ is successful  