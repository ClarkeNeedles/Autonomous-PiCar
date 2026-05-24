---
title: "Setting up camera drivers on Ubunto with raspberry Pi OV5647"
date: 2026-02-03
week: 5
hours: 3
tags: [Camera, Ubuntu, RPICam]
contributors: [Ben Malvern]
status: Completed
---

# Daily Logbook Entry Template

> **Instructions**: This is an example of a logbook template that describes work done on your project in a systematic manner. Copy this template to create your daily entries. Save as: `logbook/week-XX/YYYY-MM-DD_brief-description.md`

## Objectives

What did you plan to accomplish in this session?

- Setup camera drivers on linux (Split into multiple sessions)

## Detailed Work Log

### Session 1: [Setting up camera drivers on Ubunto with raspberry Pi OV5647] (6:30-7:30)

**Members Present**: [Ben Malvern]

**Description**:
Setup drivers in ubuntu to run the Pi OV5647 camera.

## **Materials/Tools Used**:

- **Process/Steps**:

1. Initial setup of libraries
2. Testing (Fail), test hardware (Hardware was fine)
3. Research on drivers and common issues
4. edit /dev/firmware/config.txt (camera auto detection set to 0, manual driver selection to OV5647)








**Documentation**:

<!-- Add images, diagrams, screenshots from the images/ folder -->
<!-- Store your images in: images/week-XX/ directory -->

![A giant duck.](../../images/giant_duck.jpg)

_Figure 1: Brief description of what the image shows and its relevance to your work_

### Session 2: [Activity Name] (HH:MM - HH:MM)

**Members Present**: [Name1, Name2, Name3]

**Description**:

## Results & Data

### Measurements/Observations

| Parameter | Expected | Measured | Pass/Fail | Notes |
| --------- | -------- | -------- | --------- | ----- |
|           |          |          |           |       |

### Code Snippets

```python
# Add relevant code here
```

### Calculations

Show your mathematical work:

$$
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$

## Challenges & Solutions

stream to network:

On picar:
hostname -I
rpicam-vid -t 0 --codec h264 --inline -o - | ffmpeg -re -i - -c copy -f mpegts tcp://0.0.0.0:5000?listen=1

(IP DEPENDENT)
on vlc player:

network stream from top left
tcp://192.168.2.156:5000
(replace with address)

To Run car controls:

py -m pip install keyboard (powershell)
(run script)

On Robot:
ros2 launch robocar_base cmd_vel_to_robocar.launch.py

new terminal:
python3 stdin_to_cmdvel.py



### Challenge 1: [Issue Description]

**Problem**:

**Debugging Steps**:

1.
2.
3.

**Solution**:

**Lessons Learned**:

## Next Steps

- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

## References

- [Reference 1](URL)
- [Reference 2](URL)

## Personal Notes

Any additional thoughts, observations, or things to remember...

---

**Entry completed**: YYYY-MM-DD HH:MM
