#!/bin/bash

INTERVAL=0.1

while true
do
    NAME=$(date +"%Y-%m-%d_%H-%M-%S")
    rpicam-still -n --width 640 --height 480 -o image_$NAME.jpg
    sleep $INTERVAL
done
