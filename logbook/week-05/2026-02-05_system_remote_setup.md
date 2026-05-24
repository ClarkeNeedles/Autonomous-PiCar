---
title: PiCar-X Remote Access, Network Boot Fix, and ROS Control Validation
date: 2026-02-05
duration: 2.0 hours (15:00–17:00)
project: Autonomous PiCar-X Platform
category: Development & Debugging
author: Clarke, Ben
---

# Engineering Logbook Entry

## 1. Session Objective

Establish reliable remote access and control of the PiCar-X by:

- Enabling automatic WiFi connection on boot
- Allowing SSH access without manual network intervention
- Debugging ROS control script
- Validating live camera streaming
- Evaluating sensor additions for future SLAM implementation

## 2. System State Before Session

- Pi running Ubuntu
- Manual WiFi connection required
- ROS control script inconsistent
- No reliable remote boot workflow

## 3. Work Completed

### 3.1 Automatic WiFi Connection on Boot

Configured NetworkManager using `nmcli` to auto-connect to mobile hotspot on startup.

**Issue Encountered:**

> “A start job is running for Wait for Network”

This service blocked startup indefinitely and prevented execution of network configuration.

**Resolution:**

Disabled the systemd wait-for-network service to allow immediate boot.

**Result:**

- System boots without hanging
- `nmcli` executes correctly
- Auto-connect functions as intended

### 3.2 SSH Remote Access Workflow

Developed a repeatable workflow:

1. Run PowerShell script on host machine to retrieve Pi IP address
2. Connect via SSH
3. Execute remote control script

**Result:**

- Successful SSH access
- Vehicle controllable via keyboard input over SSH

System is now operable headlessly.

### 3.3 ROS Control Script Debugging

**Initial issue:**

- ROS node launch script failed to properly control vehicle

**After troubleshooting:**

- Script executes correctly
- ROS nodes launch
- Vehicle responds to control commands

Control confirmed functional.

### 3.4 Live Camera Feed over UDP

Streamed camera feed using UDP to VLC.

**Observations:**

- Video feed stable at short distance
- Noticeable latency increase as distance from hotspot increased

**Likely Cause:**

- Bandwidth / signal strength limitations of mobile hotspot

**Potential Improvement:**

- Migrate system to QueensU-Secure WiFi for better infrastructure support

## 4. Performance Observations

| System Component | Status     | Notes                                |
|------------------|------------|--------------------------------------|
| Boot process     | Stable     | No longer blocked                    |
| Auto WiFi        | Working    | Reliable hotspot connection          |
| SSH control      | Working    | Keyboard teleoperation confirmed     |
| ROS control node | Working    | Launch + response verified           |
| Camera stream    | Functional | Latency increases with distance      |

## 5. Technical Insights

- Boot-time services (systemd dependencies) can interfere with autonomous startup behavior.
- Network reliability is currently the primary system bottleneck.
- Remote operability milestone achieved.
- Infrastructure quality significantly impacts perception system performance.

## 6. Design Considerations (Forward-Looking)

### IMU Integration for SLAM

Considering adding accelerometer/gyroscope module (e.g., MPU-6050).

**Advantages:**

- Improves pose estimation robustness
- Supports sensor fusion
- Reduces reliance on pure vision-based localization

**Integration Plan:**

- Use I2C pins on PiHat
- Fuse IMU data with vision in future SLAM milestone

## 7. Open Issues

- Network latency under weak signal
- Need quantitative latency measurement
- Camera calibration pending

## 8. Next Actions

- [ ] Configure PiCar-X on QueensU-Secure WiFi
- [ ] Calibrate camera
- [ ] Benchmark camera latency numerically
- [ ] Research and procure IMU module
- [ ] Design sensor fusion architecture for SLAM phase

## 9. System Status at End of Session

PiCar-X is now:

- Headless-operable
- Remotely controllable via SSH
- Streaming live video
- Launching ROS nodes successfully

This marks a significant infrastructure milestone enabling future autonomy development.

---

**Entry finalized:** 2026-02-05