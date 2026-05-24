---
title: "Physical Design Integration, Lane FSM Refinement and Localization Strategy"
date: 2026-02-15
week: 6
hours: 2.0
tags: [system-design, lane-following, state-machine, localization, hardware]
contributors: [Ben, Jimmy, Filip, Clarke]
---

# More Design Decisions

## Meeting Information

**Date:** 2026-02-15  
**Time:** 11:00 – 13:00  
**Duration:** 2.0 hours  
**Location:** WLH  
**Meeting Type:** Design Review / Architecture Refinement  

### Attendees

- ✅ Ben – Integration  
- ✅ Jimmy – Computer Vision  
- ✅ Filip – Hardware  
- ✅ Clarke – Autonomy  

---

## 📋 Agenda

1. Integrate physical design into overall system structure  
2. Refine system task diagram  
3. Improve lane-following architecture  
4. Discuss intersection handling via state machine  
5. Revisit localization strategy (Odometry vs IMU)  

---

## 📝 Discussion Summary

### 1. Physical Design Integration

**Context:**  
The system diagram currently focuses heavily on software architecture. We identified the need to explicitly incorporate the physical design into the overall system structure.

**Key Points Discussed:**

- The final vehicle design must be reflected in the architecture documentation  
- Physical constraints affect perception, navigation, and transport logic  
- How ducks will be safely transported  
- Ensuring transport mechanism does not interfere with camera FOV or sensors  

**Decisions Made:**

- Add physical subsystem block to system diagram  
- Explicitly model duck transport mechanism as part of system requirements  
- Treat mechanical transport as a first-class system component  

**Action Items:**

- [ ] Filip – Propose duck transport mechanism concept – **Due:** 2026-02-18  
- [ ] Clarke – Update system diagram to include physical subsystem – **Due:** 2026-02-16  

---

### 2. Refining the System Tasks Diagram

**Context:**  
The system task diagram required clearer boundaries between perception, autonomy, and control.

**Key Points Discussed:**

- Improve clarity of task ownership  
- Separate perception-triggered events from control logic  
- Ensure integration responsibilities are visible  

**Decisions Made:**

- Refactor diagram to reflect data flow rather than just feature list  
- Align task diagram with milestone structure  

**Action Items:**

- [ ] Ben – Review integration paths in updated diagram – **Due:** 2026-02-17  

---

### 3. Lane Following – Masking Strategy

**Context:**  
We evaluated improvements to the CV pipeline for lane following.

**Key Points Discussed:**

- Apply masking to isolate lane lines  
- Reduce noise and irrelevant background features  
- Improve robustness in controlled environments  

**Decisions Made:**

- Implement masking as preprocessing step before lane detection  
- Maintain compatibility with unified detection model  

**Action Items:**

- [ ] Jimmy – Prototype lane masking pipeline – **Due:** 2026-02-19  

---

### 4. Intersection Handling – State Machine Design

**Context:**  
Intersection handling requires more structured behavior than continuous PID lane tracking.

**Key Points Discussed:**

- Grayscale alone insufficient at intersections  
- CV required to detect branching and direction decisions  
- State machine could structure behavior more reliably  

**Proposed States:**

- **Lane Follow State**  
- **Intersection Detected State**  
- **Turning State**  

**State Triggers:**

- Grayscale confidence score drops  
- CV-based intersection detection  
- Explicit navigation command  

**Decisions Made:**

- Implement lane-following logic as a finite state machine (FSM)  
- Use both grayscale confidence and CV triggers for transitions  
- Keep transition conditions measurable and testable  

**Action Items:**

- [ ] Clarke – Draft FSM structure for lane following – **Due:** 2026-02-17  
- [ ] Jimmy – Define CV-based intersection trigger condition – **Due:** 2026-02-18  

---

### 5. Localization – IMU vs Odometry

**Context:**  
We discussed improving localization reliability.

**Key Points Discussed:**

- Odometry alone may accumulate error  
- Short track reduces long-term drift concerns  
- IMU provides more immediate orientation updates  
- IMU also introduces drift over time  

**Discussion Outcome:**

- Avoid relying solely on odometry  
- Fuse IMU with odometry for improved pose estimation  
- Avoid overengineering full SLAM unless necessary  

**Decisions Made:**

- Prioritize sensor fusion approach  
- Treat IMU as complementary, not replacement  

**Action Items:**

- [ ] Clarke – Evaluate IMU + odometry fusion approach – **Due:** 2026-02-20  

---

## ✅ Decisions & Outcomes

### Technical Decisions

| Decision | Rationale | Impact | Alternatives Considered |
|----------|-----------|--------|------------------------|
| Add physical subsystem to architecture | Hardware affects autonomy | Clearer system modeling | Software-only diagram |
| Use masking for lane detection | Reduce CV noise | Improved lane accuracy | Raw frame detection |
| Implement FSM for intersections | Structured behavior control | More predictable autonomy | Pure reactive control |
| Fuse IMU with odometry | Reduce pose error | Improved localization | Odometry-only |

### Project Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Model duck transport explicitly | Competition requirement clarity | Prevents late-stage redesign |
| Refine system task diagram | Improve integration clarity | Easier subsystem ownership |

---

## 📦 Action Items & Next Steps

### Immediate Actions (This Week)

- [ ] **Clarke** – Update system diagram with physical subsystem – **Due:** 2026-02-16  
- [ ] **Clarke** – Draft lane FSM – **Due:** 2026-02-17  
- [ ] **Jimmy** – Implement masking prototype – **Due:** 2026-02-19  
- [ ] **Filip** – Concept for duck transport – **Due:** 2026-02-18  

### Upcoming Actions (Next Week+)

- [ ] **Clarke** – Investigate IMU + odometry fusion – **Due:** 2026-02-20  
- [ ] **Team** – Review updated task diagram – **Due:** 2026-02-18  

### Blocked Items

- ⛔ Final localization architecture – **Blocker:** Sensor fusion validation required  

---

## 📊 Project Status

### Overall Progress

**On Track**  
Architecture becoming more structured. Major autonomy behaviors (lane following + intersections) now moving toward formalized state-based control.

### Milestones

| Milestone | Target Date | Status | Notes |
|-----------|-------------|--------|-------|
| Physical Design Integration | 2026-02-18 | ⚠️ In Progress | Transport concept pending |
| Lane FSM Implementation | 2026-02-20 | ⚠️ In Progress | Draft in progress |
| Localization Refinement | 2026-02-22 | ⏳ Upcoming | Sensor fusion evaluation |

---

## 🎯 Next Meeting

**Date:** TBD  
**Time:** TBD  
**Location:** WLH  

**Proposed Agenda:**

1. Review FSM draft  
2. Evaluate masking results  
3. Finalize duck transport design  

---

## 💬 Additional Notes

This session marked a shift toward more structured autonomy design. The move to a finite state machine for intersections significantly clarifies expected behavior. Integrating the physical design into system architecture ensures mechanical constraints are considered early rather than retrofitted later.

---

**Minutes prepared by:** Clarke  
**Date submitted:** 2026-02-15  
**Reviewed by:** Team