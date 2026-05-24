#!/bin/bash
set -e

WORKSPACE="$HOME/elec-392-project-blekinge-12/ros2_ws"

cd "$WORKSPACE"
colcon build --packages-select perception autonomy_node hardware_pkg behavior_pkg
source install/setup.bash
sleep 1   # allow camera to fully release after any prior run

# --- Video recording ---
RECORD_RAW_VIDEO=false
RECORD_DEBUG_VIDEO=true

# --- Segmentation / camera ---
CAM_WIDTH=640
CAM_HEIGHT=480
CAM_FPS=30

# --- Mask filtering ---
MASK_TOP_CROP_PERCENT=20
MIN_BLOB_AREA=50
MIN_FOLLOW_AREA=200
GREEN_MORPH_KERNEL=1
FOLLOW_ROW_START_PERCENT=80

# --- PD gains ---
KP=0.70
KD=0.0

# --- Smoothing & rate limiting ---
ALPHA=1.0
STEER_ALPHA=0.6

STEER_RATE_LIMIT=50.0
JUMP_THRESHOLD=50.0
# --- Confidence / adaptive speed ---
CONFIDENCE_SPEED_FACTOR=0.01
COAST_DURATION=0.4

# --- General driving ---
SPEED=0.5
TURN_SPEED=0.5
STEERING_GAIN=1.0
STEERING_DEADBAND=0.03
MAX_LINE_FOLLOW_ANGULAR=1.0

# --- Route: manual list of turns at each intersection ---
# Options: LEFT, RIGHT, STRAIGHT
ROUTE=""   # 5 consecutive straight throughs (no turns)

# --- Stop detection ---
CROSS_MIN_WIDTH_PCT=0.70      # p10-p90 green spread to count as intersection (raise to reduce false triggers on turns)
YELLOW_STOP_THRESHOLD=250

# --- Tank turn ---
# throttle_gain=100, so motor% = 100 * angular_speed (0.40 → 40% motor power)
TANK_TURN_ANGULAR_SPEED=0.60
TANK_TURN_TIMEOUT=9.0
PRE_TURN_DRIVE_DURATION=0.30
POST_TURN_COOLDOWN=0.6
POST_TURN_MIN_CONFIDENCE=0.5
TANK_TURN_EXIT_CENTER=0.35

# --- Line-lost recovery ---
LINE_LOST_REVERSE_SPEED=-0.60
LINE_LOST_REVERSE_DURATION=3.0

# --- Ultrasonic obstacle stop ---
ULTRASONIC_STOP_THRESHOLD_CM=8.0
ULTRASONIC_MIN_CONSECUTIVE_READS=5

# --- Hardware ---
THROTTLE_GAIN=100.0
STEER_CENTER=-8.0
STEER_MAX=38.0
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
  -p follow_row_start_percent:=$FOLLOW_ROW_START_PERCENT \
  -p line_lost_reverse_speed:=$LINE_LOST_REVERSE_SPEED \
  -p line_lost_reverse_duration:=$LINE_LOST_REVERSE_DURATION \
  -p route:=$ROUTE \
  -p cross_min_width_pct:=$CROSS_MIN_WIDTH_PCT \
  -p yellow_stop_threshold:=$YELLOW_STOP_THRESHOLD \
  -p tank_turn_angular_speed:=$TANK_TURN_ANGULAR_SPEED \
  -p tank_turn_timeout:=$TANK_TURN_TIMEOUT \
  -p pre_turn_drive_duration:=$PRE_TURN_DRIVE_DURATION \
  -p post_turn_cooldown:=$POST_TURN_COOLDOWN \
  -p post_turn_min_confidence:=$POST_TURN_MIN_CONFIDENCE \
  -p tank_turn_exit_center:=$TANK_TURN_EXIT_CENTER \
  -p record_debug_video:=$RECORD_DEBUG_VIDEO &

ros2 run hardware_pkg ultrasonic --ros-args \
  -p stop_threshold_cm:=$ULTRASONIC_STOP_THRESHOLD_CM \
  -p min_consecutive_reads:=$ULTRASONIC_MIN_CONSECUTIVE_READS &

ros2 run behavior_pkg behavior_manager --ros-args \
  -p max_speed:=1.0 \
  -p steering_filter_alpha:=0.0 &

ros2 run hardware_pkg cmd_vel_to_robocar --ros-args \
  -p throttle_gain:=$THROTTLE_GAIN \
  -p steer_center_deg:=$STEER_CENTER \
  -p steer_max_deg:=$STEER_MAX \
  -p invert_steer:=$INVERT_STEER &

wait
