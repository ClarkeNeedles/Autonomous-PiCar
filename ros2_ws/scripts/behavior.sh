#!/usr/bin/env bash

PKG="behavior_pkg"
WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"

REBUILD=true
if [[ "$1" == "--no-build" ]]; then
    REBUILD=false
fi

source /opt/ros/humble/setup.bash
cd "$WORKSPACE"

if [ "$REBUILD" = true ]; then
    colcon build --packages-select "$PKG"
fi

source "$WORKSPACE/install/setup.bash"

ros2 run "$PKG" behavior_manager

wait