---
title: "Steering Servo Calibration and ROS Driver Integration"
date: 2026-01-23
week: 3
hours: 5.0
tags: [ROS2, Servos, Calibration]
contributors: [Ben Malvern]
author: Ben Malvern
status: Completed
---

# Daily Logbook Entry Template

> **Instructions**: This is an example of a logbook template that describes work done on your project in a systematic manner. Copy this template to create your daily entries. Save as: `logbook/week-XX/YYYY-MM-DD_brief-description.md`

## Objectives

What did you plan to accomplish in this session?

-
- Calibrate steering servo center and limits
- Refine Ubuntu-compatible motor and servo drivers
- Integrate drivers with ROS velocity commands

## Detailed Work Log

### Session 1: Steering Servo Calibration (13:00 - 15:30)

**Members Present**: Ben Malvern

**Description**:  
Performed steering servo calibration to determine correct center position and mechanical limits. Tested multiple angle offsets to identify a neutral steering position and ensure symmetric left/right turning without binding or overtravel.

## **Materials/Tools Used**:

- Raspberry Pi 4
- SunFounder Robot HAT
- Steering servo
- Python

**Process/Steps**:

1. Issued incremental servo angle commands
2. Observed physical steering alignment
3. Identified neutral center offset
4. Defined safe left and right angle limits

**Documentation**:

### Session 2: ROS Driver Bridge Implementation (15:30 - 18:00)

**Members Present**: Ben Malvern

**Description**:  
Integrated calibrated servo values into a ROS node that subscribes to velocity commands. Implemented scaling and clamping to convert angular velocity commands into calibrated steering angles.

## Results & Data

### Measurements/Observations

| Parameter         | Expected        | Measured | Pass/Fail | Notes           |
| ----------------- | --------------- | -------- | --------- | --------------- |
| Servo center      | Straight wheels | Straight | Pass      | Offset applied  |
| Steering symmetry | Equal turn      | Equal    | Pass      | Limits enforced |

### Code Snippets

```python
# Steering calibration values applied within ROS velocity callback
```
