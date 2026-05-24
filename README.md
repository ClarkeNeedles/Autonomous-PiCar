# Autonomous Robotic Taxi

A safety-first autonomous taxi built for the Town of Quackston using a SunFounder PiCar-X, ROS 2, computer vision, and a Google Coral Edge TPU.

This repository contains the full autonomy stack developed by Team Rust-eze for Queen's ELEC 392. The vehicle follows lanes, detects stop lines, plans routes through a miniature city, interfaces with the Vehicle Positioning and Fare System (VPFS), picks up and drops off duck passengers, signals its intentions, and stops for obstacles.

### Tech Stack

* Python / C++
* ROS2
* OpenCV for vision processing
* Raspberry Pi hardware platform
* Linux robotics environment

## Table of Contents

- [Project Overview](#project-overview)
- [What This Repository Demonstrates](#what-this-repository-demonstrates)
- [System Architecture](#system-architecture)
- [Performance Highlights](#performance-highlights)
- [Project Structure](#project-structure)
- [Hardware Requirements](#hardware-requirements)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Running the System](#running-the-system)
- [Calibration and Utilities](#calibration-and-utilities)
- [Development Notes](#development-notes)
- [Course Information](#course-information)
- [License](#license)

## Project Overview

The goal of this project was to design and validate an autonomous taxi for Quackston, a miniature city with lane markings, intersections, stop lines, pedestrians, and fare pickup/drop-off tasks. The final design uses a modular ROS 2 Humble architecture running on the vehicle's Raspberry Pi.

The stack is organized around five main responsibilities:

- **Perception**: A TensorFlow Lite semantic segmentation model classifies camera pixels as background, green lane markings, or yellow stop lines.
- **Control**: A PD lane-following controller converts the segmentation mask into velocity commands and steering corrections.
- **Behavior Management**: A finite state machine coordinates driving, stopping, fare handling, turn execution, and safety overrides.
- **Localization and Fare Handling**: A VPFS bridge receives global vehicle pose and fare data from the external Quackston system.
- **Navigation**: A graph-based map planner uses Dijkstra's algorithm to create turn queues for pickup and drop-off routes.

Safety is treated as the first design priority. The vehicle includes ultrasonic obstacle detection, emergency stop behavior, rear brake lights, turn signals, hazard signaling, audio alerts, and a CARE passenger restraint system.

## What This Repository Demonstrates

- A full ROS 2 autonomy stack split into perception, behavior, navigation, localization, control, and hardware packages.
- Real-time camera-based lane following using semantic segmentation on a Coral Edge TPU.
- Stop-line detection using the same vision pipeline as lane detection.
- VPFS integration for autonomous taxi fare selection, pickup, and drop-off.
- Dijkstra route planning over a directed map of Quackston.
- Turn-queue execution at intersections, including tank-steering behavior.
- ROS-to-hardware control for PiCar-X motors, steering, LEDs, and sensors.
- Safety logic that can pause or stop the vehicle when obstacles are detected.
- A development logbook used to document design decisions, subsystem trade-offs, integration issues, testing results, and weekly progress.
- Recordings that demonstrate autonomous driving behavior and show how the segmentation model interprets the road.
- Docker-based development workflows for testing ROS 2 nodes in a consistent environment before deploying to the vehicle.
- Calibration tools, setup scripts, model artifacts, recordings, and final-report documentation.

## System Architecture

The robot is built as a set of ROS 2 nodes that communicate through topics:

| Subsystem | Package | Key Nodes | Role |
| --- | --- | --- | --- |
| Perception and autonomy | `perception` | `segmentation_node`, `autonomy_node` | Runs Edge TPU segmentation, filters masks, follows lanes, detects stop lines, publishes `/cmd_vel`, `/tank_steer`, and `/turn_signal_cmd`. |
| Behavior management | `behavior_pkg` | `behavior_manager` | High-level finite state machine for fare state, driving permission, pickup/drop-off flow, and safety coordination. |
| Navigation | `navigation_pkg` | `map_planner` | Loads Quackston map CSVs, computes shortest paths, and publishes turn queues. |
| Localization and VPFS | `localization_pkg` | `vpfs_queue_bridge`, `vpfs`, `odometry` | Polls VPFS for pose and fare information and publishes route context. |
| Hardware interface | `hardware_pkg` | `cmd_vel_to_robocar`, `ultrasonic`, `grayscale` | Converts ROS commands to Robot HAT motor/servo actions and publishes sensor states. |
| Control experiments | `control_pkg` | `lane_follow`, `pid` | C++ control prototypes and experiments. |
| Base robot utilities | `robocar_base` | camera, recorder, command bridge nodes | Supporting robot drivers and development utilities. |

Core topic flow:

```text
camera -> segmentation_node -> /segmentation/mask -> autonomy_node
autonomy_node -> /cmd_vel, /tank_steer, /turn_signal_cmd -> cmd_vel_to_robocar
ultrasonic -> /ultrasonic/detected -> behavior_manager and hardware safety logic
vpfs_queue_bridge -> /odometry/filtered, /vpfs/current_fare -> behavior_manager
behavior_manager -> /navigation/current_pose, /navigation/target_pose -> map_planner
map_planner -> /navigation/turn_queue -> autonomy/behavior logic
behavior_manager -> /autonomy/driving_allowed -> autonomy_node
```

## Performance Highlights

The final report documents the following validation results:

- **Semantic segmentation validation accuracy**: approximately **98.9%**, exceeding the 96% target.
- **Straight-line lane following**: completed all consecutive straight-line trials.
- **Left turns**: **4/4** successful trials.
- **Right turns**: **3/4** successful trials, with the remaining issue attributed mainly to lighting.
- **Stop behavior**: **20/20** complete stops in stop-condition trials.
- **Obstacle emergency stop**: **5/5** successful controlled ultrasonic stop trials.
- **Full autonomous fare-style runs**: **2/4** completed in integrated testing.

The competition run itself was affected by a software deployment/version-control issue, so controlled validation trials are the better representation of the system's actual capability.

Supporting recordings are included in `recordings/`. These videos were used during development to review the vehicle's behavior, inspect the generated segmentation output, and debug how perception, lane following, stop detection, and turning logic interacted during real runs.

## Project Structure

```text
Autonomous-PiCar/
|-- README.md
|-- LICENSE
|-- requirements.txt
|-- setup_coral.sh
|-- setup_picarx.sh
|-- ELEC392_Final_Report.pdf
|-- segmentation_models/
|   |-- segmentation_v5.tflite
|   |-- segmentation_final_edgetpu*.tflite
|-- ros2_ws/
|   |-- scripts/
|   |   |-- run.sh
|   |   |-- line_follow.sh
|   |   |-- line_follow_fast.sh
|   |   |-- behavior.sh
|   |   |-- localization.sh
|   |   |-- navigation.sh
|   |   |-- emergency_stop.sh
|   |   |-- vpfs_queue_system.sh
|   |   |-- controller.py
|   |   |-- stdin_to_cmdvel.py
|   |   `-- timelapse.sh
|   |-- src/
|   |   |-- behavior_pkg/
|   |   |   |-- src/behavior_manager.cpp
|   |   |   |-- CMakeLists.txt
|   |   |   `-- package.xml
|   |   |-- control_pkg/
|   |   |   |-- src/lane_follow.cpp
|   |   |   |-- src/pid.cpp
|   |   |   |-- CMakeLists.txt
|   |   |   `-- package.xml
|   |   |-- hardware_pkg/
|   |   |   |-- hardware_pkg/cmd_vel_to_robocar.py
|   |   |   |-- hardware_pkg/ultrasonic.py
|   |   |   |-- hardware_pkg/grayscale.py
|   |   |   |-- hardware_pkg/speaker.py
|   |   |   |-- launch/
|   |   |   |-- setup.py
|   |   |   `-- package.xml
|   |   |-- localization_pkg/
|   |   |   |-- localization_pkg/vpfs_queue_bridge.py
|   |   |   |-- localization_pkg/vpfs.py
|   |   |   |-- localization_pkg/odometry.py
|   |   |   |-- setup.py
|   |   |   `-- package.xml
|   |   |-- navigation_pkg/
|   |   |   |-- src/mapping.cpp
|   |   |   |-- config/map_nodes.csv
|   |   |   |-- config/map_edges.csv
|   |   |   |-- CMakeLists.txt
|   |   |   `-- package.xml
|   |   |-- perception/
|   |   |   |-- perception/segmentation_node.py
|   |   |   |-- perception/autonomy_node.py
|   |   |   |-- launch/line_following.launch.py
|   |   |   |-- test_mask_output.py
|   |   |   |-- setup.py
|   |   |   `-- package.xml
|   |   `-- robocar_base/
|   |       |-- robocar_base/cmd_vel_to_robocar.py
|   |       |-- robocar_base/rpi_cam_stream_node.py
|   |       |-- robocar_base/video_recorder_node.py
|   |       |-- robocar_base/camera.py
|   |       |-- launch/
|   |       |-- setup.py
|   |       `-- package.xml
|   `-- robot-hat/
|       `-- Robot HAT Python driver library and docs
|-- utils/
|   |-- actuator_calibration.py
|   |-- camera_calibration.py
|   |-- capture_images.py
|   |-- detection_receiver.py
|   |-- detection_sender.py
|   |-- grayscale_calibration.py
|   |-- servo_zeroing.py
|   `-- troubleshooting.md
|-- images/
|   |-- camera_calibration/
|   |-- week3/
|   |-- week5/
|   |-- week7/
|   |-- week8/
|   |-- week-09/
|   |-- week-10/
|   `-- week-12/
|-- recordings/
|-- sound/
`-- logbook/
    |-- README.md
    |-- generate_activity_report.py
    |-- week-01/
    |-- week-02/
    |-- week-03/
    |-- week-04/
    |-- week-05/
    |-- week-06/
    |-- week-07/
    |-- week-08/
    |-- week-09/
    |-- week-10/
    `-- week-12/
```

## Hardware Requirements

- SunFounder PiCar-X robot car
- Raspberry Pi 4B or compatible Raspberry Pi capable of running ROS 2
- Google Coral USB Accelerator
- Raspberry Pi camera module or compatible camera
- Ultrasonic distance sensor
- Line tracking/grayscale sensors
- Robot HAT motor/servo controller
- Rear brake lights, left/right turn signals, and visible warning LEDs
- Speaker or audio output for alert sounds
- CARE passenger restraint system
- Printed AprilTag for VPFS tracking

## Software Requirements

- Ubuntu Server or Raspberry Pi OS compatible with ROS 2 deployment
- ROS 2 Humble
- Python 3.9+
- C++17-compatible compiler for ROS 2 C++ packages
- TensorFlow Lite runtime
- Coral Edge TPU runtime and compiler support
- OpenCV
- Colcon and standard ROS 2 build tools
- Robot HAT Python drivers
- See `requirements.txt` for Python dependencies

## Installation

Clone the repository on the Raspberry Pi:

```bash
git clone <repository-url>
cd Autonomous-PiCar
```

Install the PiCar-X and Robot HAT dependencies:

```bash
bash setup_picarx.sh
```

Install Coral USB Accelerator dependencies:

```bash
bash setup_coral.sh
```

Build the ROS 2 workspace:

```bash
cd ros2_ws
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
```

## Running the System

The main integrated runner is:

```bash
cd ros2_ws
bash scripts/run.sh
```

Useful options:

```bash
# Skip rebuilding before launch
bash scripts/run.sh --no-build

# Enable debug logging for key autonomy, VPFS, and planner nodes
bash scripts/run.sh --debug
```

Targeted launch scripts are also available in `ros2_ws/scripts/` for line following, behavior, localization, navigation, emergency stop testing, and VPFS queue testing.

### Common ROS 2 Commands

Run the perception pipeline:

```bash
ros2 run perception segmentation_node
ros2 run perception autonomy_node
```

Run hardware control:

```bash
ros2 run hardware_pkg cmd_vel_to_robocar
ros2 run hardware_pkg ultrasonic
```

Run high-level autonomy components:

```bash
ros2 run behavior_pkg behavior_manager
ros2 run localization_pkg vpfs_queue_bridge
ros2 run navigation_pkg map_planner
```

## Calibration and Utilities

Calibration scripts are provided for setup and hardware bring-up:

```bash
# Zero servos to a known neutral position
python utils/servo_zeroing.py

# Calibrate motor and steering behavior
python utils/actuator_calibration.py

# Calibrate grayscale sensors
python utils/grayscale_calibration.py

# Capture camera data for calibration or model development
python utils/capture_images.py

# Run camera calibration
python utils/camera_calibration.py
```

Additional troubleshooting notes are available in `utils/troubleshooting.md`.

## Development Notes

- The autonomy stack is intentionally modular so each subsystem can be tested independently with `ros2 topic echo`, `ros2 topic pub`, and package-specific launch scripts.
- Docker containers were used to keep ROS 2 development and node testing consistent across machines, reducing dependency drift while perception, hardware, behavior, navigation, and localization nodes were developed in parallel.
- The vision model was trained from vehicle camera data collected in the Quackston environment and labeled with pixel-wise masks.
- Training used augmentation for lighting, motion blur, exposure variation, shear, and noise before conversion to TensorFlow Lite for Edge TPU deployment.
- Navigation map data lives in `ros2_ws/src/navigation_pkg/config/map_nodes.csv` and `ros2_ws/src/navigation_pkg/config/map_edges.csv`.
- Development history, design decisions, rejected alternatives, testing notes, integration lessons, and weekly progress are documented in `logbook/`.
- Driving and debug recordings in `recordings/` provide visual evidence of the segmentation model and autonomy stack operating on the Quackston course.
- The final engineering report is included as `ELEC392_Final_Report.pdf`.

## Course Information

**Course**: ELEC 392 - Engineering Design and Development  
**Institution**: Smith Engineering, Queen's University  
**Offering**: Winter 2026  
**Team**: Rust-eze / Blekinge 12

## License

See `LICENSE` for details.
