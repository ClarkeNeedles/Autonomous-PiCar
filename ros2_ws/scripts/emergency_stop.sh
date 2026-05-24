#!/bin/bash
set -euo pipefail

WORKSPACE="${WORKSPACE:-$HOME/elec-392-project-blekinge-12/ros2_ws}"
MODE="${1:-stop}"
PUB_RATE_HZ="${PUB_RATE_HZ:-10}"
DETECTED_TOPIC="/ultrasonic/detected"
RESUME_TOPIC="/emergency_resume"

cd "$WORKSPACE"
source install/setup.bash

publish_resume() {
  echo "Publishing resume on ${RESUME_TOPIC} and clearing ${DETECTED_TOPIC}"
  ros2 topic pub --once "$RESUME_TOPIC" std_msgs/msg/Bool "{data: true}"
  ros2 topic pub --once "$DETECTED_TOPIC" std_msgs/msg/Bool "{data: false}"
}

run_stop_latch() {
  echo "Emergency stop active"
  echo "Publishing ${DETECTED_TOPIC}=true at ${PUB_RATE_HZ} Hz until ${RESUME_TOPIC} is received"
  echo "Resume with: $0 resume"

  ros2 topic pub -r "$PUB_RATE_HZ" "$DETECTED_TOPIC" std_msgs/msg/Bool "{data: true}" &
  PUBLISHER_PID=$!

  cleanup() {
    if kill -0 "$PUBLISHER_PID" 2>/dev/null; then
      kill "$PUBLISHER_PID" 2>/dev/null || true
      wait "$PUBLISHER_PID" 2>/dev/null || true
    fi
  }

  trap cleanup EXIT INT TERM

  ros2 topic echo --once "$RESUME_TOPIC" std_msgs/msg/Bool >/dev/null

  echo "Resume received"
  cleanup
  ros2 topic pub --once "$DETECTED_TOPIC" std_msgs/msg/Bool "{data: false}"
  trap - EXIT INT TERM
}

case "$MODE" in
  stop)
    run_stop_latch
    ;;
  resume)
    publish_resume
    ;;
  *)
    echo "Usage: $0 [stop|resume]"
    exit 1
    ;;
esac
