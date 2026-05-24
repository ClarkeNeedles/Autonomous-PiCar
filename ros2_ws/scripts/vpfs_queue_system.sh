#!/usr/bin/env bash
set -euo pipefail

PKGS=(localization_pkg behavior_pkg navigation_pkg)
WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"

REBUILD=true
if [[ "${1:-}" == "--no-build" ]]; then
    REBUILD=false
fi

cleanup() {
    for pid in "${PIDS[@]:-}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done

    for pid in "${PIDS[@]:-}"; do
        wait "$pid" 2>/dev/null || true
    done
}

trap cleanup EXIT INT TERM

set +u
source /opt/ros/humble/setup.bash
cd "$WORKSPACE"

if [[ "$REBUILD" == true ]]; then
    colcon build --packages-select "${PKGS[@]}"
fi

source "$WORKSPACE/install/setup.bash"
set -u

declare -a PIDS=()

ros2 run localization_pkg vpfs_queue_bridge &
PIDS+=($!)

ros2 run behavior_pkg behavior_manager &
PIDS+=($!)

ros2 run navigation_pkg map_planner &
PIDS+=($!)

echo "VPFS queue system running:"
echo "  - localization_pkg/vpfs_queue_bridge"
echo "  - behavior_pkg/behavior_manager"
echo "  - navigation_pkg/map_planner"
echo
echo "Use Ctrl+C to stop all three nodes."

wait
