---
title: "Localization Strategy & CV Model Planning + Data Collection Testing"
date: 2026-02-12
week: 6
hours: 2.5
tags: [localization, computer-vision, data-collection, TPU, testing]
contributors: [Ben, Jimmy, Filip, Clarke]
---

# Meeting Minutes Template

## Meeting Information

**Date:** 2026-02-12  
**Time:** 16:30 – 19:00  
**Duration:** 2.5 hours  
**Location:** WLH  
**Meeting Type:** Technical Design Discussion / Experimental Testing  

### Attendees

- ✅ Ben – Integration  
- ✅ Jimmy – Computer Vision  
- ✅ Filip – Hardware  
- ✅ Clarke – Autonomy  

---

## 📋 Agenda

1. Discuss localization approach (Ben’s recommendations)
2. Refine lane-following node design
3. Computer vision model architecture decisions
4. TPU model deployment strategy
5. Collect training data (record video while driving)
6. Diagnose camera instability issues

---

## 📝 Discussion Summary

### 1. Localization Discussion

**Context:**  
Reviewed feedback from Ben regarding localization architecture and integration constraints.

**Key Points Discussed:**
- How localization integrates with autonomy stack
- Interaction between localization and navigation
- Avoiding unnecessary architectural complexity

**Decisions Made:**
- Continue refining localization assumptions before committing to major structural changes
- Keep architecture flexible while evaluating perception and navigation constraints

**Action Items:**
- [ ] Document updated localization assumptions – **Owner:** Clarke – **Due:** 2026-02-14  
- [ ] Validate integration requirements – **Owner:** Ben – **Due:** 2026-02-15  

---

### 2. Lane Following Node – Intersection Handling

**Context:**  
Discussed robustness of grayscale lane sensing at intersections.

**Key Points Discussed:**
- Grayscale sensors become unreliable at intersections
- Lane contrast may disappear or become ambiguous
- CV-based lane detection is more adaptable in complex scenes

**Decisions Made:**
- Use grayscale for normal lane tracking (efficient + low latency)
- At intersections, fall back to CV-only mode
- Incorporate this logic into the lane fusion node

**Action Items:**
- [ ] Define intersection detection trigger – **Owner:** Jimmy – **Due:** 2026-02-16  
- [ ] Update lane fusion logic design – **Owner:** Clarke – **Due:** 2026-02-16  

---

### 3. Computer Vision Model Strategy

**Context:**  
Discussed how to structure models for lane detection and object detection on the TPU.

**Key Points Discussed:**
- Instant segmentation for object detection
- Whether to deploy multiple models to TPU:
  - One for lane detection
  - One for object detection
- Compute budget remains similar whether using multiple smaller models or one unified model

**Decisions Made:**
- Prefer training a single YOLOv8 model for both lane and object detection
- Avoid redundant model loading on TPU
- Use multi-class detection within one architecture

**Action Items:**
- [ ] Begin dataset labeling strategy for combined model – **Owner:** Jimmy – **Due:** 2026-02-18  
- [ ] Evaluate TPU deployment constraints – **Owner:** Jimmy – **Due:** 2026-02-18  

---

### 4. Data Collection – Filming for Model Training

**Context:**  
Collected training data by manually driving the car and recording video.

**Procedure for Filming While Controlling the Car**

**Step 1 - Launch base control stack (on Pi):**

[Launch File](../../ros2_ws/src/robocar_base/launch/cmd_vel_to_robocar.launch.py)

**Step 2 - Run the following on the Pi:**

[Steering Node](../../ros2_ws/src/robocar_base/robocar_base/stdin_to_cmdvel.py)

**Step 3 - In your local terminal run:**

[Controller File](../../ros2_ws/scripts/controller.py)

**Step 4 - To start recording (on the Pi terminal):**

`rpicam-vid -t 0
--width 960
--height 540
--framerate 60
--codec h264
-o video.h264`

press `ctrl+c` to stop recording

**Step 5 - Convert to mp4:**

`ffmpeg -framerate 60 -i video.h264 -c copy video.mp4`


**Key Observations:**
- Video was initially very shaky
- This affects training quality and labeling accuracy

---

### 5. Camera Shake & Hardware Improvements

**Context:**  
Video instability significantly impacted data quality.

**Issues Identified:**
- Double-sided tape on Pi camera had not been properly removed
- Camera mount was unstable
- Wheel treads caused vibration

**Improvements Tested:**
- Properly securing the camera with tape attached correctly
- Removing problematic treads improved stability
- Significant improvement observed after securing camera

**Proposed Hardware Improvements:**
- 3D print flatter treads
- Design TPU 3D-printed flexible camera mount
- Improve vibration damping structurally rather than compensating in software

**Decisions Made:**
- Prioritize mechanical stability before further data collection
- 3D print new treads
- Explore TPU-based flex mount design

**Action Items:**
- [ ] Filip – Prototype TPU flexible camera mount – **Due:** 2026-02-19  
- [ ] Team – Re-record training footage after hardware improvements – **Due:** 2026-02-20  

---

## ✅ Decisions & Outcomes

### Technical Decisions

| Decision | Rationale | Impact | Alternatives Considered |
|----------|-----------|--------|------------------------|
| CV-only fallback at intersections | Grayscale unreliable in complex layouts | More robust lane tracking | Always-fused pipeline |
| Single YOLOv8 model | Efficient TPU usage | Simpler deployment | Multiple separate models |
| Improve hardware before retraining | Data quality directly impacts model performance | Better training dataset | Software stabilization only |

### Project Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Formalize filming procedure | Reproducible dataset collection | Cleaner workflow |
| Assign clear subsystem owners | Maintain parallel progress | Improved accountability |

---

## 📦 Action Items & Next Steps

### Immediate Actions (This Week)

- [ ] **Filip** – Print new wheel treads? – **Due:** 2026-02-17  
- [ ] **Clarke** – Implement intersection fallback logic – **Due:** 2026-02-16  

### Upcoming Actions (Next Week+)

- [ ] **Filip** – TPU flexible mount prototype – **Due:** 2026-02-19  
- [ ] **Team** – Collect stabilized training footage – **Due:** 2026-02-20  

### Blocked Items

- ⛔ High-quality model training – **Blocker:** Camera instability and vibration

---

## 📊 Project Status

### Overall Progress

**On Track**  
Clear direction established for CV pipeline and hardware stabilization before large-scale data collection.

### Milestones

| Milestone | Target Date | Status | Notes |
|-----------|-------------|--------|-------|
| Hardware Stabilization | 2026-02-19 | ⚠️ In Progress | New treads + mount |
| Lane Following Improvements | 2026-02-20 | ⚠️ In Progress | Intersection logic pending |
| Unified Object Detection Model | 2026-02-25 | ⏳ Upcoming | Dataset prep started |

---

## 🎯 Next Meeting

**Date:** 2026-02-15  
**Time:** TBD  
**Location:** WLH  

**Proposed Agenda:**
1. Review stabilized footage
2. YOLOv8 dataset progress
3. Lane fusion intersection logic update

---

## 💬 Additional Notes

This session highlighted how strongly hardware quality affects ML performance. Improving physical stability is currently more impactful than additional model tuning. The shift toward a unified detection model simplifies deployment and aligns well with TPU constraints.

---

**Minutes prepared by:** Clarke  
**Date submitted:** 2026-02-12  
**Reviewed by:** Team  