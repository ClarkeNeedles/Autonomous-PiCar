---
title: "Navigation Package – Map Planner and Route Generation"
date: "2026-03-17"
time: "N/A"
contributors: ["Ben Malvern", "Clarke Needles", "Jimmy Moutafis-Tymcio", "Filip Radenovic"]
tags: ["ROS2", "Navigation", "Path Planning", "Graph", "Routing"]
---

## Overview
This session focused on developing the **navigation package**, specifically the map planner node responsible for generating routes through the map and providing turn-by-turn instructions to the rest of the system.

The navigation node converts the robot’s current pose and a target destination into:
- A sequence of nodes (path)
- A queue of turn instructions (LEFT, STRAIGHT, RIGHT)

This enables higher-level nodes (autonomy and behavior manager) to execute structured navigation decisions.

---

## Agenda
- Implement map-based routing system  
- Load map data from CSV files  
- Generate shortest path between current and target positions  
- Compute turn instructions for intersections  
- Integrate planner outputs with autonomy and behavior manager  

---

## Navigation Package Structure
- The navigation node is implemented in C++ within the navigation package  
- Uses CSV-based map representation:
  - `map_nodes.csv` → node positions  
  - `map_edges.csv` → graph connectivity  

- Core components:
  - Road graph representation  
  - Shortest path algorithm  
  - Turn classification logic  

**Reference Implementation:**
```
elec-392-project-blekinge-12\ros2_ws\src\navigation_pkg\src\mapping.cpp
```

---

## Discussion Summary

### Map Representation
- The environment is modeled as a **directed graph**:
  - Nodes represent positions/intersections  
  - Edges represent valid paths between nodes  

- Each node contains:
  - ID  
  - (x, y) position  
  - Optional label  

- Each edge contains:
  - Start node  
  - End node  
  - Cost (distance or weighted value)  

---

### Path Planning (Shortest Path)
- Implemented using a **Dijkstra-style algorithm**:
  - Computes lowest-cost path from start to goal  
  - Uses priority queue for efficient traversal  

- Process:
  1. Determine closest graph node to current position  
  2. Determine closest graph node to target position  
  3. Compute shortest path between nodes  

- Output:
  - Ordered list of node IDs representing the path  

---

### Start Edge Selection
- Instead of snapping directly to a node, the planner:
  - Determines the **best edge alignment** based on:
    - Distance to edge  
    - Heading alignment  
    - Remaining path cost  

- This improves:
  - Path accuracy  
  - Alignment with robot orientation  

- If no valid edge is found:
  - Falls back to nearest-node planning  

---

### Turn Classification
- After computing the path, the planner generates a **turn queue**  

- Method:
  - For each triple of nodes (A → B → C):
    - Compute angle between segments  
    - Classify as:
      - LEFT (0)  
      - STRAIGHT (1)  
      - RIGHT (2)  

- Output:
  ```
  /navigation/turn_queue
  ```

---

### ROS2 Integration

#### Inputs
- `/navigation/current_pose` (Pose2D)
- `/navigation/target_pose` (Pose2D)

#### Outputs
- `/navigation/next_node` → next waypoint  
- `/navigation/path_nodes` → full path (string format)  
- `/navigation/turn_queue` → sequence of turns  

---

### Communication with Other Nodes

#### With Behavior Manager
- Behavior manager uses:
  - `turn_queue` to determine upcoming actions at intersections  
  - `next_node` for progress tracking  

- Enables:
  - Decision making at intersections  
  - Synchronization between planning and execution  

#### With Autonomy Node
- Autonomy node:
  - Executes turns based on `turn_queue`  
  - Uses perception (segmentation) to detect intersections  
  - Pops turns from queue as they are completed  

---

### System Flow
```
VPFS / Odometry → Navigation Planner
        ↓
   Path + Turn Queue
        ↓
   Behavior Manager
        ↓
   Autonomy Node (lane following + turning)
        ↓
   Hardware Node
```

---

## Key Decisions
- Use graph-based navigation instead of reactive-only driving  
- Implement shortest path planning using Dijkstra  
- Generate explicit turn queue for deterministic intersection handling  
- Integrate tightly with behavior manager for execution  

---

## Action Items
- [ ] Validate map accuracy and node placement  
- [ ] Tune edge snapping and heading thresholds  
- [ ] Test navigation across multiple routes  
- [ ] Ensure synchronization between planner and autonomy node  
- [ ] Handle dynamic replanning if path changes  

---

## Notes
- Edge-based start selection significantly improves initial alignment  
- Turn queue abstraction simplifies downstream control logic  
- Navigation layer enables structured, goal-driven behavior  
- System is modular and integrates cleanly with perception and control  