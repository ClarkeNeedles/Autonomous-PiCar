---
title: "Hardware Package – Sensor Integration and Updates"
date: "2026-03-17"
time: "N/A"
contributors: ["Ben Malvern", "Clarke Needles", "Jimmy Moutafis-Tymcio", "Filip Radenovic"]
tags: ["ROS2", "Hardware", "Sensors", "Ultrasonic", "Integration"]
---

## Overview
This session focused on expanding the **hardware package** to reliably acquire sensor data and integrate it into the ROS2 system. The hardware package serves as the interface between the RoboCar’s physical sensors and the software stack.

Key updates included stabilizing the ultrasonic sensor after hardware fixes and making a design decision to transition away from the grayscale sensor in favor of a fully computer vision-based approach.

---

## Agenda
- Implement sensor nodes within hardware package  
- Validate ultrasonic sensor performance after hardware adjustments  
- Evaluate grayscale sensor usage  
- Improve integration between hardware and higher-level nodes  

---

## Hardware Package Structure
- All sensor and hardware interface nodes are located in:
  ```
  elec-392-project-blekinge-12\ros2_ws\src\hardware_pkg\hardware_pkg
  ```

- Responsibilities of the hardware package:
  - Read raw sensor data from physical components  
  - Publish processed sensor data to ROS2 topics  
  - Provide clean and reliable inputs for higher-level nodes (behavior, perception)  

---

## Discussion Summary

### Ultrasonic Sensor Node
- Implemented a dedicated ROS2 node for the ultrasonic sensor  
- Publishes obstacle detection status to:
  ```
  /ultrasonic/detected
  ```

- Detection logic:
  - Uses distance threshold (≈15 cm)  
  - Requires multiple consecutive readings to confirm detection  
  - Applies filtering to reduce noise  

**Reference Implementation:**
```
elec-392-project-blekinge-12\ros2_ws\src\hardware_pkg\hardware_pkg\ultrasonic.py
```  

---

### Ultrasonic Hardware Fix
- Initial issue:
  - Sensor readings were inconsistent and unreliable  
  - Caused by interference from nearby **metal bracket**

- Fix:
  - Applied **electrical tape** to isolate the sensor  

- Result:
  - Readings are now **stable and accurate**  
  - Minimal noise and near-zero offset  
  - Sensor is reliable enough for obstacle detection  

- Additional validation performed using calibration script  

**Reference Test Script:**
```
elec-392-project-blekinge-12\ros2_ws\src\hardware_pkg\hardware_pkg\ultrasonic_calib.py
``` 

---

### Sensor Data Processing
- Implemented:
  - Basic filtering (exponential smoothing)  
  - Threshold-based detection logic  
  - Consecutive reading validation to prevent false positives  

- Output:
  - Clean Boolean signal indicating obstacle presence  
  - Directly usable by behavior manager and hardware safety systems  

---

### Grayscale Sensor Decision
- Initially used for line following and lane detection  
- Calibration was performed previously, but:

- Key issues:
  - Sensitive to lighting conditions  
  - Requires frequent recalibration  
  - Less robust compared to vision-based methods  

- **Decision:**
  - Transition away from grayscale sensor  
  - Rely entirely on **computer vision (lane segmentation + object detection)**  

- Benefits:
  - More flexible and scalable  
  - Better alignment with overall perception pipeline  
  - Reduces hardware dependency and calibration overhead  

---

### Hardware Integration with Control
- Sensor outputs are integrated with control systems:
  - Ultrasonic detection feeds into safety logic  
  - Used for:
    - Emergency stopping  
    - Hazard light activation  

- Hardware node (`cmd_vel_to_robocar`) subscribes to:
  - `/ultrasonic/detected` for hazard signaling  

**Reference Implementation:**
```
elec-392-project-blekinge-12\ros2_ws\src\hardware_pkg\hardware_pkg\cmd_vel_to_robocar.py
```

---

## Key Decisions
- Ultrasonic sensor is now stable and will be used for obstacle detection  
- Remove grayscale sensor from main pipeline  
- Transition fully to vision-based perception system  
- Keep hardware layer focused on **reliable, minimal sensor outputs**  

---

## Action Items
- [ ] Remove grayscale sensor node from active system  
- [ ] Validate ultrasonic performance during motion  
- [ ] Integrate ultrasonic detection into behavior manager logic  
- [ ] Test full system with CV-only lane following  
- [ ] Monitor for any remaining sensor noise or edge cases  

---

## Notes
- Hardware fixes can significantly impact sensor reliability  
- Simpler sensor pipelines reduce debugging complexity  
- CV-based perception provides a more robust long-term solution  
- Ultrasonic sensor now acts as the primary short-range safety mechanism  