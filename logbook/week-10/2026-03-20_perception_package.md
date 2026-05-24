---
title: "Perception Package – Segmentation and Lane Following Integration"
date: "2026-03-20"
time: "N/A"
contributors: ["Ben Malvern", "Clarke Needles", "Jimmy Moutafis-Tymcio", "Filip Radenovic"]
tags: ["ROS2", "Perception", "Segmentation", "PID", "Autonomy"]
---

## Overview
This session focused on developing and integrating the **perception package**, which enables the RoboCar to perform lane following using a segmentation model and a PID-based control system.

The perception pipeline consists of:
- A **segmentation node** that processes camera input and produces a semantic mask  
- An **autonomy node** that uses this mask to compute steering commands via a PID controller  

This system forms the core of the robot’s lane-following capability and communicates directly with the behavior manager for execution.

---

## Agenda
- Implement segmentation-based perception pipeline  
- Integrate segmentation output with autonomy node  
- Implement PID-based lane following  
- Connect perception outputs to behavior manager  

---

## Perception Package Structure
- All perception-related nodes are located in:
  ```
  elec-392-project-blekinge-12\ros2_ws\src\perception\perception
  ```

- Key components:
  - `segmentation_node.py` → runs ML model and outputs mask  
  - `autonomy_node.py` → processes mask and generates control commands  

---

## Discussion Summary

### Segmentation Node
- Implemented a segmentation pipeline using a **TensorFlow Lite model on the Coral accelerator**  
- Captures camera frames and performs real-time inference  

- Outputs:
  - `/segmentation/mask` → pixel-wise classification (lane, stop line, background)  
  - `/segmentation/green_pixels` → number of detected lane pixels  
  - `/segmentation/fps` → performance monitoring  

- Key functionality:
  - Converts camera feed into semantic mask  
  - Identifies:
    - Green lane (drivable path)  
    - Yellow stop lines  
  - Runs efficiently using EdgeTPU acceleration  

**Reference Implementation:**
```
elec-392-project-blekinge-12\ros2_ws\src\perception\perception\segmentation_node.py
```

---

### Autonomy Node (Lane Following)
- Consumes segmentation output:
  ```
  /segmentation/mask
  ```

- Core functionality:
  - Extract lane position from mask  
  - Compute steering error relative to center of image  
  - Apply **PID control (PD in implementation)** to generate steering commands  

- Control approach:
  - Proportional term (kp): corrects lateral error  
  - Derivative term (kd): dampens oscillations  
  - Additional smoothing and filtering applied to reduce noise  

- Output:
  ```
  /cmd_vel
  ```
  - `linear.x` → forward speed  
  - `angular.z` → steering command  

**Reference Implementation:**
```
elec-392-project-blekinge-12\ros2_ws\src\perception\perception\autonomy_node.py
```

---

### Lane Following Pipeline
1. Camera captures frame  
2. Segmentation node processes frame → outputs mask  
3. Autonomy node:
   - Extracts lane centroid from mask  
   - Computes normalized steering error  
   - Applies PID control  
4. Outputs `/cmd_vel` to be consumed by behavior manager  

---

### State Machine and Robustness
- The autonomy node includes a **state machine** for handling different scenarios:
  - `LINE_FOLLOWING` → normal operation  
  - `LINE_LOST` → recovery behavior  
  - `STOPPING` → stop line detection  
  - `TURNING / TANK_TURNING` → intersection handling  

- Additional features:
  - Confidence-based speed adjustment  
  - Error smoothing and rate limiting  
  - Line-loss recovery using reverse motion  

---

### Communication with Behavior Manager
- The autonomy node publishes:
  ```
  /cmd_vel
  ```
- This is consumed by the **behavior manager**, which:
  - Applies higher-level logic (obstacle avoidance, mission logic, etc.)  
  - Modifies or overrides commands if necessary  
  - Sends final commands to the hardware node  

- Additional communication:
  - Turn signals via `/turn_signal_cmd`  
  - Tank steering mode via `/tank_steer`  

- This creates a layered architecture:
  ```
  Perception (segmentation + autonomy)
        ↓
  Behavior Manager
        ↓
  Hardware Node
  ```

---

## Key Decisions
- Use segmentation-based perception instead of traditional sensors  
- Implement PID (PD) control for stable lane following  
- Keep perception focused on generating clean control signals  
- Delegate higher-level decision making to behavior manager  

---

## Action Items
- [ ] Tune PID gains (kp, kd) for smoother lane following  
- [ ] Optimize segmentation model performance if needed  
- [ ] Test lane following under different lighting conditions  
- [ ] Improve robustness of line-loss recovery  
- [ ] Validate full pipeline with behavior manager and hardware  

---

## Notes
- Segmentation provides a robust and flexible perception method  
- PID control allows smooth and stable steering adjustments  
- Clear separation between perception and behavior simplifies debugging  
- This pipeline replaces the need for grayscale-based lane detection  