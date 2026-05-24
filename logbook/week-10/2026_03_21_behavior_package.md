---
title: "Behavior Manager – System Integration and State Control"
date: "2026-03-21"
time: "N/A"
contributors: ["Ben Malvern", "Clarke Needles", "Jimmy Moutafis-Tymcio", "Filip Radenovic"]
tags: ["ROS2", "Behavior", "State Machine", "Integration", "Control"]
---

## Overview
This session focused on developing the **behavior manager**, which acts as the **central coordination node** of the entire RoboCar system.

The behavior manager ties together:
- Perception (segmentation + autonomy)  
- Navigation (map planner)  
- Localization (VPFS / odometry)  
- Hardware (motors, sensors)  

It manages high-level system states, controls when the robot is allowed to move, and orchestrates transitions between different operational phases.

This node is effectively the **centerpiece of the entire system architecture**.

---

## Agenda
- Implement centralized behavior management node  
- Integrate VPFS, navigation, and autonomy systems  
- Design system state machine  
- Handle obstacle detection and safety logic  
- Refine system behavior under multiple simultaneous inputs  

---

## Discussion Summary

### Behavior Manager Role
- The behavior manager acts as a **decision-making layer** between planning and execution  

- Responsibilities:
  - Manage system state (fare handling, navigation progress, obstacle handling)  
  - Control when the robot is allowed to move  
  - Publish target poses to the navigation planner  
  - Process VPFS fare data and manage mission lifecycle  

- Key communication:
  - Inputs:
    - `/vpfs/current_fare`  
    - `/odometry/filtered`  
    - `/ultrasonic/detected`  
  - Outputs:
    - `/autonomy/driving_allowed`  
    - `/navigation/current_pose`  
    - `/navigation/target_pose`  

**Reference Implementation:**
```
elec-392-project-blekinge-12\ros2_ws\src\behavior_pkg\src\behavior_manager.cpp
```

---

### System State Machine

The behavior manager uses a **state machine** to manage fare execution:

#### Core States
- `NO_FARE`
- `GO_TO_PICKUP`
- `WAIT_FOR_PICKUP_POSITION`
- `WAIT_FOR_PICKUP_CONFIRM`
- `GO_TO_DROPOFF`
- `WAIT_FOR_DROPOFF_POSITION`
- `WAIT_FOR_DROPOFF_CONFIRM`

---

### State Transitions
- **NO_FARE → GO_TO_PICKUP**
  - Triggered when a new fare is received  

- **GO_TO_PICKUP → WAIT_FOR_PICKUP_POSITION**
  - When robot reaches pickup threshold distance  

- **WAIT_FOR_PICKUP_POSITION → WAIT_FOR_PICKUP_CONFIRM**
  - When `inPosition = true` from VPFS  

- **WAIT_FOR_PICKUP_CONFIRM → GO_TO_DROPOFF**
  - When `pickedUp = true`  

- **GO_TO_DROPOFF → WAIT_FOR_DROPOFF_POSITION**
  - When robot reaches dropoff threshold  

- **WAIT_FOR_DROPOFF_POSITION → WAIT_FOR_DROPOFF_CONFIRM**
  - When `inPosition = true`  

- **WAIT_FOR_DROPOFF_CONFIRM → NO_FARE**
  - When `completed = true`  

---

### Obstacle Handling
- Uses ultrasonic sensor input:
  ```
  /ultrasonic/detected
  ```

- Behavior:
  - Immediately stops driving when obstacle detected  
  - Enters a **hold state** for a fixed duration  
  - Rechecks obstacle before resuming  

- Adds robustness by:
  - Preventing rapid toggling  
  - Ensuring safe stopping behavior  

---

### Driving Control
- Behavior manager does **not directly control motors**  
- Instead, it publishes:
  ```
  /autonomy/driving_allowed
  ```

- The autonomy node:
  - Generates `/cmd_vel`  
  - Only executes movement if `driving_allowed = true`  

---

### Architecture Experiment (Motor Control Separation)

#### Attempted Approach
- Tried to **move motor control logic out of the autonomy node**  
- Intended architecture:
  ```
  Autonomy → Behavior Manager → Hardware
  ```

#### Result
- This caused:
  - Increased complexity  
  - Poor system responsiveness  
  - Conflicts between control signals  

- Likely issues:
  - Multiple nodes publishing simultaneously  
  - Delays in command propagation  
  - Loss of tight feedback loop between perception and control  

#### Final Decision
- Reverted to:
  ```
  Autonomy → Hardware (direct control)
  Behavior Manager → gating only
  ```

- This approach:
  - Worked reliably  
  - Maintained responsive control  
  - Simplified system behavior  

---

### System Complexity Challenges
- The system has **many topics publishing simultaneously**, including:
  - Perception outputs  
  - Navigation updates  
  - VPFS updates  
  - Sensor data  

- Observed issues:
  - Occasional undefined behavior  
  - State transitions occurring mid-update  
  - Conflicting signals between nodes  

- Hypothesis:
  - System may become **overwhelmed or desynchronized**  
  - Messages arriving out of sync can cause inconsistent states  

---

### Refinement and Debugging
- Testing focused on:
  - Simplifying state transitions  
  - Adding clearer logging  
  - Reducing unnecessary complexity  

- Improvements:
  - More structured state handling  
  - Clearer separation of responsibilities  
  - Easier debugging through consistent logs  

---

## System Architecture Role
```
Perception (Segmentation + Autonomy)
        ↓
Behavior Manager (State + Coordination)
        ↓
Navigation Planner (Path + Turns)
        ↓
Hardware Node (Execution)
```

- Behavior manager sits at the **center**, coordinating all subsystems  

---

## Key Decisions
- Keep behavior manager as **central coordination node**  
- Do not move motor control away from autonomy node  
- Use behavior manager for **gating and state management only**  
- Prioritize simplicity and reliability over architectural purity  

---

## Action Items
- [ ] Further refine state transitions to avoid edge cases  
- [ ] Add more logging for debugging complex interactions  
- [ ] Test system under heavy message load  
- [ ] Investigate synchronization strategies if issues persist  
- [ ] Ensure consistent timing across nodes  

---

## Notes
- Centralized state management is critical for system stability  
- Over-engineering control flow can degrade performance  
- Direct control loops (autonomy → hardware) are more reliable  
- System complexity must be carefully managed to avoid undefined behavior  