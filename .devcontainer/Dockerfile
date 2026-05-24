FROM osrf/ros:humble-desktop

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-requests \
    nlohmann-json3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Optional but useful
RUN rosdep init || true

ENV DEBIAN_FRONTEND=noninteractive