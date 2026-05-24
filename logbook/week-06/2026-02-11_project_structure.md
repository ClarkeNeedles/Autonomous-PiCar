---
title: "Project Architecture Planning and Milestone Definition"
date: 2026-02-11
week: 6
hours: 3.0
tags: [planning, architecture, milestones, ROS2, system-design]
contributors: [Ben, Clarke, Jimmy, Filip]
---

# Meeting Minutes Template

## Meeting Information

**Date:** 2026-02-11  
**Time:** 16:00 – 19:00  
**Duration:** 3.0 hours  
**Location:** BMH Floor 2  
**Meeting Type:** Sprint Planning / System Architecture Planning  

### Attendees

- ✅ Ben - Integration
- ✅ Clarke - Autonomy
- ✅ Jimmy - CV
- ✅ Filip - Hardware

---

## 📋 Agenda

1. Plan overall system architecture
2. Define measurable milestones
3. Split responsibilities for parallel development
4. Discuss SLAM vs VPFS + global camera
5. Finalize ROS node and topic diagram

---

## 📝 Discussion Summary

### 1. Project Planning & Structure

**Context:**  
We were struggling with quantifying project progress and clearly splitting responsibilities. Development had become sequential instead of parallel due to unclear ownership and undefined milestones.

**Key Points Discussed:**

- Need measurable progress indicators
- Difficulty tracking how well subsystems are performing
- Lack of actionable task breakdown
- Importance of enabling parallel development
- Need clearer milestone definitions

**Decisions Made:**

- Break the project into high-level technical milestones
- Define subsystem ownership
- Convert each milestone into actionable tasks
- Use node/topic diagrams to clarify architecture boundaries

**Action Items:**

- [ ] Finalize milestone breakdown – **Owner:** Clarke – **Due:** 2026-02-23  
- [ ] Assign subsystem leads – **Owner:** Team – **Due:** 2026-02-23  

---

### 2. Main Milestones Defined

**Context:**  
We structured the entire system into layered milestones that build toward full autonomy.

**Key Points Discussed:**

- Hardware and low-level control must be stable first
- Perception and control modules should be independently testable
- System integration must be treated as its own milestone

**Milestones Identified:**

1. **Hardware + Low-Level Control**
2. **Lane Following**
   - Develop lane fusion node
   - Fuse grayscale-based detection with computer vision pipeline
3. **Object Detection**
4. **Localization**
5. **Navigation**
6. **System Integration**

**Decisions Made:**

- Create a lane fusion node combining grayscale sensor data and CV-based lane detection
- Treat system integration as a separate milestone rather than assuming it happens naturally

**Action Items:**

- [ ] Define lane fusion architecture – **Owner:** Jimmy – **Due:** 2026-02-23  
- [ ] Validate low-level motor control stability – **Owner:** Ben – **Due:** 2026-02-23  

---

### 3. SLAM vs VPFS + Global Camera

**Context:**  
We discussed whether SLAM is necessary given that we have a VPFS system and a global bird’s-eye camera.

**Key Points Discussed:**

- If VPFS provides accurate pose, SLAM may be redundant
- Navigation stack (Nav2) may still require depth or obstacle information
- Ultrasonic sensor could supplement object detection
- Need to evaluate whether we require a depth model for Nav2 compatibility

**Decisions Made:**

- Postpone full SLAM integration decision
- Investigate compatibility of VPFS pose with Nav2
- Consider ultrasonic sensor for obstacle avoidance if depth camera is not used

**Action Items:**

- [ ] Test VPFS pose compatibility with Nav2 – **Owner:** Clarke – **Due:** 2026-02-29  
- [ ] Evaluate ultrasonic-based obstacle detection – **Owner:** Team Member 2 – **Due:** 2026-02-29  

---

### 4. ROS Node & Topic Structure Diagram

**Context:**  
The ROS node and topic architecture needs to clearly reflect subsystem boundaries and data flow.

**Key Points Discussed:**

- Diagram must show node ownership and responsibilities
- Topic naming conventions should be standardized
- Visualization helps identify redundant or missing data flows

**Decisions Made:**

- Complete architecture diagram before implementing additional nodes
- Use diagram as reference for future logs and documentation

**Action Items:**

- [ ] Finish ROS node/topic diagram – **Owner:** Clarke – **Due:** 2026-02-23  
- [ ] Review naming conventions for consistency – **Owner:** Team – **Due:** 2026-02-23  

---

## ✅ Decisions & Outcomes

### Technical Decisions

| Decision | Rationale | Impact | Alternatives Considered |
|----------|-----------|--------|------------------------|
| Define layered milestones | Enables measurable progress | Improves planning & delegation | Ad-hoc development |
| Lane fusion node | Improves robustness using sensor fusion | More modular perception stack | Single detection pipeline |
| Delay SLAM decision | Avoid unnecessary complexity | Keeps architecture flexible | Immediate SLAM integration |

### Project Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Explicit task delegation | Enables parallel development | Faster iteration |
| Treat integration as milestone | Avoids last-minute system failures | Better system stability |

---

## 📦 Action Items & Next Steps

### Immediate Actions (This Week)

- [ ] **Clarke** – Finalize architecture diagram – **Due:** 2026-02-23  
- [ ] **Ben** – Validate motor control performance – **Due:** 2026-02-23  
- [ ] **Jimmy** – Draft lane fusion node structure – **Due:** 2026-02-23  

### Upcoming Actions (Next Week+)

- [ ] **Clarke** – Nav2 compatibility testing with VPFS – **Due:** 2026-02-29  
- [ ] **Team** – Obstacle detection evaluation strategy – **Due:** 2026-02-29  

### Blocked Items

- ⛔ SLAM decision – **Blocker:** Need Nav2 + VPFS compatibility testing results

---

## 📊 Project Status

### Overall Progress

**On Track**  

Clear milestone definition significantly improved structure and delegation ability.

### Milestones

| Milestone | Target Date | Status | Notes |
|-----------|-------------|--------|-------|
| Hardware + Low-Level Control | 2026-02-14 | ⚠️ In Progress | Stability testing ongoing |
| Lane Following | 2026-02-20 | ⏳ Upcoming | Awaiting fusion design |
| Object Detection | TBD | ⏳ Upcoming | |
| Localization | TBD | ⏳ Upcoming | VPFS evaluation pending |
| Navigation | TBD | ⏳ Upcoming | Dependent on localization |
| System Integration | TBD | ⏳ Upcoming | Final milestone |

---

## 🎯 Next Meeting

**Date:** 2026-02-12  
**Time:** TBD  
**Location:** WLH  

**Proposed Agenda:**

1. Review architecture diagram
2. Motor control validation results
3. Lane fusion node design

---

## 💬 Additional Notes

This meeting significantly improved clarity around project direction. Defining structured milestones and actionable tasks enables parallel subsystem development and provides measurable progress indicators moving forward.

---

**Minutes prepared by:** Clarke  
**Date submitted:** 2026-02-11  
**Reviewed by:** Team