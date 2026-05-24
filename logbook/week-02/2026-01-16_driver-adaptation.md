---
title: "Ubuntu Bring-Up and Initial Motor/Servo Driver Adaptation"
date: 2026-01-16
week: 2
hours: 4.0
tags: [Ubuntu, Drivers, Motors]
contributors: [Ben Malvern]
author: Ben Malvern
status: Completed
---

# Daily Logbook Entry Template

> **Instructions**: This is an example of a logbook template that describes work done on your project in a systematic manner. Copy this template to create your daily entries. Save as: `logbook/week-XX/YYYY-MM-DD_brief-description.md`

## Objectives

What did you plan to accomplish in this session?

-
- Adapt SunFounder motor and servo drivers for Ubuntu compatibility
- Verify low-level motor and servo control on Raspberry Pi
- Establish a stable hardware control baseline

## Detailed Work Log

### Session 1: Driver Compatibility Investigation (15:00 - 17:00)

**Members Present**: Ben Malvern

**Description**:  
Reviewed SunFounder Robot HAT motor and servo drivers to identify incompatibilities with Ubuntu on Raspberry Pi. Determined that several scripts assumed Raspberry Pi OS–specific configurations. Investigated GPIO access, permissions, and library paths required for Ubuntu support.

## **Materials/Tools Used**:

- Raspberry Pi 4
- Ubuntu
- SunFounder Robot HAT libraries
- Python

**Process/Steps**:

1. Audited existing driver source files
2. Identified OS-specific assumptions
3. Tested basic GPIO and PWM access under Ubuntu

**Documentation**:

### Session 2: Initial Driver Rewrites (17:00 - 19:00)

**Members Present**: Ben Malvern

**Description**:  
Rewrote portions of the motor and servo drivers to function correctly under Ubuntu. Updated imports, permissions, and control logic to allow motors and servos to respond to direct test commands.

## Results & Data

### Measurements/Observations

| Parameter      | Expected        | Measured | Pass/Fail | Notes               |
| -------------- | --------------- | -------- | --------- | ------------------- |
| Motor response | Forward/reverse | Correct  | Pass      | Stable under Ubuntu |
| Servo movement | Angle control   | Working  | Pass      | Calibration pending |

### Code Snippets

```python
# Ubuntu-compatible motor and servo driver adaptations
```
