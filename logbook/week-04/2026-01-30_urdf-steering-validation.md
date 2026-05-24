---
title: "Validated Steering Control and Initial URDF Robot Model"
date: 2026-01-30
week: 4
hours: 4
tags: [URDF, Gazebo, ROS2]
contributors: [Ben Malvern]
author: Ben Malvern
status: Completed
---

# Daily Logbook Entry Template

> **Instructions**: This is an example of a logbook template that describes work done on your project in a systematic manner. Copy this template to create your daily entries. Save as: `logbook/week-XX/YYYY-MM-DD_brief-description.md`

## Objectives

What did you plan to accomplish in this session?

- Validate calibrated steering under ROS control
- Confirm stability of rewritten motor and servo drivers
- Create an initial URDF model of the robot

## Detailed Work Log

### Session 1: Steering and Driver Validation (14:00 - 16:00)

**Members Present**: Ben Malvern

**Description**:  
Tested calibrated steering servo under repeated ROS velocity commands. Verified consistent centering, predictable turning behavior, and stable response during start/stop motion. Confirmed no driver crashes or unexpected behavior.

## **Materials/Tools Used**:

- Raspberry Pi 4
- Ubuntu
- ROS 2
- Custom motor and servo drivers

**Process/Steps**:

1. Executed repeated steering commands
2. Observed alignment consistency
3. Monitored driver stability

**Documentation**:

### Session 2: Initial URDF Modeling (16:00 - 18:00)

**Members Present**: Ben Malvern

**Description**:  
Created an initial URDF describing the robot chassis, wheel placement, and steering geometry. Used approximate dimensions to enable early Gazebo visualization.

## Results & Data

### Measurements/Observations

| Parameter              | Expected       | Measured   | Pass/Fail | Notes              |
| ---------------------- | -------------- | ---------- | --------- | ------------------ |
| Steering repeatability | Consistent     | Consistent | Pass      | Calibration stable |
| URDF visualization     | Correct layout | Partial    | Pass      | Needs refinement   |

### Code Snippets

```python
# URDF created separately; no executable code in this session
```
