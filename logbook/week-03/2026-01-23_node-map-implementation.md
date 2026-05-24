---
title: Implementation of Topological Node Map & Pathfinding
date: 2026-01-23
week: 03
author: Filip Radenovic
hours: 5.0
status: Completed
tags: [software, python, pathfinding, quackston, dijkstra]
---

## 1. Objective

To implement the core navigation logic for the PiCar-X in the "Quackston" environment. This involves creating a directed graph representation of the town's streets and implementing Dijkstra's algorithm to calculate optimal routes between 26 discrete nodes.

## 2. Technical Implementation

### 2.1 Graph Data Structure

I implemented a custom directed graph using two primary classes to handle the specific "town" constraints (e.g., one-way streets):

1. **`Connection`**: Stores the destination node (`to_node`), the cardinal direction (`direction`), and a traversal weight (`estimated_time`).
2. **`Snode` (Street Node)**: Represents an intersection or location ID and holds a list of outgoing `Connection` objects.

```python
# Code Snippet: Graph definitions
class Connection:
    def __init__(self, to_node, direction, estimated_time=1):
        self.to_node = to_node
        self.direction = direction
        self.estimated_time = estimated_time

class Snode:
    def __init__(self, node_id, connections=None):
        self.node_id = node_id
        self.connections = connections if connections else []
```

### 2.2 Algorithm Complexity Analysis

For pathfinding, I utilized Dijkstra's algorithm with a Min-Priority Queue (via Python's `heapq` module). To satisfy the system's real-time constraints, I analyzed the computational complexity to ensure it wouldn't block the main control loop.

For a graph with $V$ vertices and $E$ edges using a binary heap:
- Extracting the minimum element takes $O(\log V)$.
- We perform this operation once per vertex ($V$ times).
- We perform a relaxation step (decrease-key) potentially for every edge ($E$ times).

The total time complexity is:

$$T(V,E) = O(V\log V + E\log V) = O((V+E)\log V)$$

With our map size of 26 nodes, this complexity is negligible, allowing for rapid re-calculation if the robot misses a turn.

### 2.3 Map Topology Verification

The map was initialized manually with 26 nodes. I verified the connectivity logic by overlaying the node IDs onto the visual street map to ensure no "island" nodes (unreachable areas) were created.

![Figure 1: Visual verification of node placement](../../images/week-03/node-placement.png)
*Figure 1: Visual verification of node placement.

## 3. Challenges & Solutions

**Challenge 1: Handling "Infinitely" Distant Nodes**

- **Issue**: During initial testing, if a target node was unreachable (due to a one-way street configuration error), the algorithm would return the initialization value of infinity but the vehicle controller tried to interpret this as a valid time.
- **Solution**: I added a specific check at the reconstruction phase. If the destination distance remains `float('inf')`, the function now returns an empty path list, signaling the main controller to stop or request a new target.

```python
# Path reconstruction safety check
if distances[end_node_id] == float('inf'):
    return float('inf'), []
```

**Challenge 2: Coordinate System Mismatch**

- **Issue**: The map's "North" did not align with the PiCar's internal compass "North," causing the `direction` attribute in the `Connection` class to be inverted.
- **Solution**: I established a global coordinate frame where Node 1 is the North-most point relative to Node 2, and updated the adjacency list manually to match this frame.

## 4. Results

The implementation was tested with a route from Node 1 to Node 26.

- **Path Found**: `[1, 4, 9, 13, 14, 15, 23, 26]`
- **Total Cost**: 7 units
- **Verification**: The path successfully navigates the one-way constraints of the Quackston layout.
