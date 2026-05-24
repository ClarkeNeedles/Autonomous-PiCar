#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"

REBUILD=true
DEBUG_LOG=false
for arg in "$@"; do
    [[ "$arg" == "--no-build" ]] && REBUILD=false
    [[ "$arg" == "--debug" ]]    && DEBUG_LOG=true
done

# When --debug is set, key nodes log at DEBUG level so FARE_JSON, FARE_NAV,
# and PLAN messages are all visible.
LOG_LEVEL_BEHAVIOR="info"
LOG_LEVEL_VPFS="info"
LOG_LEVEL_PLANNER="info"
if [[ "$DEBUG_LOG" == true ]]; then
    LOG_LEVEL_BEHAVIOR="debug"
    LOG_LEVEL_VPFS="debug"
    LOG_LEVEL_PLANNER="debug"
fi

# ---------------------------------------------------------------------------
# Config — Video recording
# ---------------------------------------------------------------------------
RECORD_RAW_VIDEO=false
RECORD_DEBUG_VIDEO=false

# ---------------------------------------------------------------------------
# Config — Segmentation / camera
# ---------------------------------------------------------------------------
CAM_WIDTH=640
CAM_HEIGHT=480
CAM_FPS=30

# ---------------------------------------------------------------------------
# Config — Mask filtering
# ---------------------------------------------------------------------------
MASK_TOP_CROP_PERCENT=20
MIN_BLOB_AREA=50
MIN_FOLLOW_AREA=200
GREEN_MORPH_KERNEL=1
FOLLOW_ROW_START_PERCENT=80

# ---------------------------------------------------------------------------
# Config — PD gains
# ---------------------------------------------------------------------------
KP=0.70
KD=0.0

# ---------------------------------------------------------------------------
# Config — Smoothing & rate limiting
# ---------------------------------------------------------------------------
ALPHA=1.0
STEER_ALPHA=0.6
STEER_RATE_LIMIT=50.0
JUMP_THRESHOLD=50.0

# ---------------------------------------------------------------------------
# Config — Confidence / adaptive speed
# ---------------------------------------------------------------------------
CONFIDENCE_SPEED_FACTOR=0.01
COAST_DURATION=0.4

# ---------------------------------------------------------------------------
# Config — General driving
# ---------------------------------------------------------------------------
SPEED=0.5
TURN_SPEED=0.5
STEERING_GAIN=1.0
STEERING_DEADBAND=0.03
MAX_LINE_FOLLOW_ANGULAR=1.0

# ---------------------------------------------------------------------------
# Config — Route (manual override; leave empty to use VPFS navigation)
#   Options per intersection: LEFT, RIGHT, STRAIGHT
# ---------------------------------------------------------------------------
ROUTE=""

# ---------------------------------------------------------------------------
# Config — Intersection / stop detection
# ---------------------------------------------------------------------------
CROSS_MIN_WIDTH_PCT=0.45
YELLOW_STOP_THRESHOLD=250
YELLOW_STOP_DURATION=0.3

# ---------------------------------------------------------------------------
# Config — Tank turn
# ---------------------------------------------------------------------------
TANK_TURN_ANGULAR_SPEED=0.6
TANK_TURN_TIMEOUT=9.0
PRE_TURN_DRIVE_DURATION=0.30
POST_TURN_COOLDOWN=1.1
POST_TURN_MIN_CONFIDENCE=0.7
TANK_TURN_EXIT_CENTER=0.25

# ---------------------------------------------------------------------------
# Config — Line-lost recovery
# ---------------------------------------------------------------------------
LINE_LOST_REVERSE_SPEED=-0.60
LINE_LOST_REVERSE_DURATION=3.0

# ---------------------------------------------------------------------------
# Config — Ultrasonic obstacle stop
# ---------------------------------------------------------------------------
ULTRASONIC_STOP_THRESHOLD_CM=8.0
ULTRASONIC_MIN_CONSECUTIVE_READS=5

# ---------------------------------------------------------------------------
# Config — Hardware
# ---------------------------------------------------------------------------
THROTTLE_GAIN=100.0
STEER_CENTER=-8.0
STEER_MAX=38.0
INVERT_STEER=false

# ---------------------------------------------------------------------------
# Config — VPFS
# ---------------------------------------------------------------------------
VPFS_URL="http://192.168.0.100:5000"
VPFS_TEAM_ID=46
VPFS_AUTH="3aa5fcda383fcfa27a63751a0fa738fc"
VPFS_POSE_POLL_HZ=2.0
VPFS_FARES_POLL_HZ=1.0

# ---------------------------------------------------------------------------
# Cleanup — kill all background nodes on exit
# ---------------------------------------------------------------------------
declare -a PIDS=()

drop_current_fare() {
    local response fare_id
    response=$(curl -sf "${VPFS_URL}/fares/current/${VPFS_TEAM_ID}?auth=${VPFS_AUTH}" 2>/dev/null) || return 0
    fare_id=$(python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    fare = d.get('fare') or d.get('current_fare')
    if fare is None and isinstance(d.get('id'), int):
        fare = d
    print(fare['id'] if fare else '')
except Exception:
    print('')
" <<< "$response")
    [[ -z "$fare_id" ]] && return 0
    echo "[run.sh] Dropping fare ${fare_id}..."
    curl -sf "${VPFS_URL}/fares/drop/${fare_id}?auth=${VPFS_AUTH}" >/dev/null 2>&1 || true
}

cleanup() {
    drop_current_fare
    for pid in "${PIDS[@]:-}"; do
        kill -0 "$pid" 2>/dev/null && kill "$pid" 2>/dev/null || true
    done
    for pid in "${PIDS[@]:-}"; do
        wait "$pid" 2>/dev/null || true
    done
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Build & source
# ---------------------------------------------------------------------------
set +u
source /opt/ros/humble/setup.bash
cd "$WORKSPACE"

if [[ "$REBUILD" == true ]]; then
    colcon build --packages-select \
        perception autonomy_node hardware_pkg behavior_pkg \
        localization_pkg navigation_pkg
fi

source "$WORKSPACE/install/setup.bash"
set -u

# Drop any fare still held from a previous run
drop_current_fare

# Kill any lingering camera process from a previous run, then wait for it to release
pkill -SIGTERM -f rpicam-vid 2>/dev/null || true
sleep 2  # allow camera to fully release after any prior run

# ---------------------------------------------------------------------------
# Launch nodes
# ---------------------------------------------------------------------------
ros2 run perception segmentation_node --ros-args \
  -p record_raw_video:=$RECORD_RAW_VIDEO \
  -p record_debug_video:=$RECORD_DEBUG_VIDEO \
  -p debug_log_every_n_frames:=0 \
  -p camera_width:=$CAM_WIDTH \
  -p camera_height:=$CAM_HEIGHT \
  -p camera_fps:=$CAM_FPS &
PIDS+=($!)

# Build route arg: omit entirely when empty so ROS2 uses the node default ("")
AUTONOMY_ROUTE_ARG=()
[[ -n "$ROUTE" ]] && AUTONOMY_ROUTE_ARG=(-p "route:=$ROUTE")

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
  "${AUTONOMY_ROUTE_ARG[@]}" \
  -p cross_min_width_pct:=$CROSS_MIN_WIDTH_PCT \
  -p yellow_stop_threshold:=$YELLOW_STOP_THRESHOLD \
  -p yellow_stop_duration:=$YELLOW_STOP_DURATION \
  -p tank_turn_angular_speed:=$TANK_TURN_ANGULAR_SPEED \
  -p tank_turn_timeout:=$TANK_TURN_TIMEOUT \
  -p pre_turn_drive_duration:=$PRE_TURN_DRIVE_DURATION \
  -p post_turn_cooldown:=$POST_TURN_COOLDOWN \
  -p post_turn_min_confidence:=$POST_TURN_MIN_CONFIDENCE \
  -p tank_turn_exit_center:=$TANK_TURN_EXIT_CENTER \
  -p record_debug_video:=$RECORD_DEBUG_VIDEO &
PIDS+=($!)

ros2 run hardware_pkg ultrasonic --ros-args \
  -p stop_threshold_cm:=$ULTRASONIC_STOP_THRESHOLD_CM \
  -p min_consecutive_reads:=$ULTRASONIC_MIN_CONSECUTIVE_READS &
PIDS+=($!)

ros2 run behavior_pkg behavior_manager --ros-args \
  --log-level "$LOG_LEVEL_BEHAVIOR" &
PIDS+=($!)

ros2 run hardware_pkg cmd_vel_to_robocar --ros-args \
  -p throttle_gain:=$THROTTLE_GAIN \
  -p steer_center_deg:=$STEER_CENTER \
  -p steer_max_deg:=$STEER_MAX \
  -p invert_steer:=$INVERT_STEER &
PIDS+=($!)

ros2 run localization_pkg vpfs_queue_bridge --ros-args \
  -p vpfs_url:=$VPFS_URL \
  -p team_id:=$VPFS_TEAM_ID \
  -p auth:=$VPFS_AUTH \
  -p pose_poll_hz:=$VPFS_POSE_POLL_HZ \
  -p fares_poll_hz:=$VPFS_FARES_POLL_HZ \
  --log-level "$LOG_LEVEL_VPFS" &
PIDS+=($!)

NODES_FILE="$WORKSPACE/install/navigation_pkg/share/navigation_pkg/config/map_nodes.csv"
EDGES_FILE="$WORKSPACE/install/navigation_pkg/share/navigation_pkg/config/map_edges.csv"

ros2 run navigation_pkg map_planner --ros-args \
  -p nodes_file:="$NODES_FILE" \
  -p edges_file:="$EDGES_FILE" \
  --log-level "$LOG_LEVEL_PLANNER" &
PIDS+=($!)

echo "All nodes started. Press Ctrl+C to stop."
wait
