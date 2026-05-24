#!/bin/bash
set -e

WORKSPACE="$HOME/elec-392-project-blekinge-12/ros2_ws"

cd "$WORKSPACE"
#colcon build --packages-select perception hardware_pkg
source install/setup.bash

# --- Video recording ---
RECORD_RAW_VIDEO=true
RECORD_DEBUG_VIDEO=false

# --- Segmentation / camera ---
CAM_WIDTH=640
CAM_HEIGHT=480
CAM_FPS=30

# --- Mask filtering ---
MASK_TOP_CROP_PERCENT=15   # ignore top N% of mask
MIN_BLOB_AREA=40           # minimum green blob area in pixels (filters noise specks)
MIN_FOLLOW_AREA=300       # green pixels needed to stay in LINE_FOLLOWING (default 2000 is too strict)
GREEN_MORPH_KERNEL=3       # morphology kernel size (1 = off)

# --- PD gains ---
KP=0.79   # proportional gain on filtered error
KD=1.50  # derivative gain — damps overshoot on straights

# --- Smoothing & rate limiting ---
ALPHA=0.75          # error low-pass: faster tracking helps catch corners early
STEER_ALPHA=0.86    # steering output low-pass: smooths remaining noise
STEER_RATE_LIMIT=0.50  # fast enough for corners, not so fast it wobbles
JUMP_THRESHOLD=0.6    # reject error jumps larger than this

# --- Confidence / adaptive speed ---
CONFIDENCE_SPEED_FACTOR=0.5   # speed reduction fraction at zero confidence
COAST_DURATION=0.4            # seconds to coast on last heading before LINE_LOST

# --- General driving ---
SPEED=2.0
TURN_SPEED=0.4
STEERING_GAIN=1.0
STEERING_DEADBAND=0.03
MAX_LINE_FOLLOW_ANGULAR=1.0
ROUTE="STRAIGHT,STRAIGHT,STRAIGHT"

# --- Intersection detection ---
INTERSECTION_WIDTH_THRESHOLD=60   # raw green px/row average to detect intersection
NORMAL_WIDTH_THRESHOLD=20         # narrow threshold to confirm intersection passed

# --- Tank turn at intersection ---
# throttle_gain=100, so turn_pct = 100 * angular_speed (e.g. 0.40 → 40% motor)
TANK_TURN_ANGULAR_SPEED=0.40      # motor power for tank turn
TANK_TURN_MIN_GREEN=400           # green pixels needed to confirm lane acquired
TANK_TURN_CONFIRM_FRAMES=3        # consecutive frames required
TANK_TURN_TIMEOUT=6.0             # safety fallback (seconds)

# --- Line-lost recovery ---
LINE_LOST_REVERSE_SPEED=-0.80
LINE_LOST_REVERSE_DURATION=4.0

# --- Hardware (tuned values from hardware_pkg launch) ---
THROTTLE_GAIN=100.0
STEER_CENTER=-8.0
STEER_MAX=35.0
INVERT_STEER=false

ros2 run perception segmentation_node --ros-args \
  -p record_raw_video:=$RECORD_RAW_VIDEO \
  -p record_debug_video:=$RECORD_DEBUG_VIDEO \
  -p debug_log_every_n_frames:=0 \
  -p camera_width:=$CAM_WIDTH \
  -p camera_height:=$CAM_HEIGHT \
  -p camera_fps:=$CAM_FPS &

ros2 run perception autonomy_node --ros-args \
  -p speed:=$SPEED \
  -p turn_speed:=$TURN_SPEED \
  -p kp:=$KP \
  -p kd:=$KD \
  -p alpha:=$ALPHA \
  -p steer_alpha:=$STEER_ALPHA \
  -p steer_rate_limit:=$STEER_RATE_LIMIT \
  -p jump_threshold:=$JUMP_THRESHOLD \
  -p confidence_speed_factor:=$CONFIDENCE_SPEED_FACTOR \
  -p coast_duration:=$COAST_DURATION \
  -p steering_gain:=$STEERING_GAIN \
  -p steering_deadband:=$STEERING_DEADBAND \
  -p max_line_follow_angular:=$MAX_LINE_FOLLOW_ANGULAR \
  -p mask_top_crop_percent:=$MASK_TOP_CROP_PERCENT \
  -p min_blob_area:=$MIN_BLOB_AREA \
  -p min_follow_area:=$MIN_FOLLOW_AREA \
  -p green_morph_kernel:=$GREEN_MORPH_KERNEL \
  -p line_lost_reverse_speed:=$LINE_LOST_REVERSE_SPEED \
  -p line_lost_reverse_duration:=$LINE_LOST_REVERSE_DURATION \
  -p route:=$ROUTE \
  -p intersection_width_threshold:=$INTERSECTION_WIDTH_THRESHOLD \
  -p normal_width_threshold:=$NORMAL_WIDTH_THRESHOLD \
  -p tank_turn_angular_speed:=$TANK_TURN_ANGULAR_SPEED \
  -p tank_turn_min_green:=$TANK_TURN_MIN_GREEN \
  -p tank_turn_confirm_frames:=$TANK_TURN_CONFIRM_FRAMES \
  -p tank_turn_timeout:=$TANK_TURN_TIMEOUT \
  -p record_debug_video:=$RECORD_DEBUG_VIDEO &

ros2 run hardware_pkg cmd_vel_to_robocar --ros-args \
  -p throttle_gain:=$THROTTLE_GAIN \
  -p steer_center_deg:=$STEER_CENTER \
  -p steer_max_deg:=$STEER_MAX \
  -p invert_steer:=$INVERT_STEER &

wait
