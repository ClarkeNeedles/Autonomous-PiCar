import sys
from pathlib import Path

# Add the repo root (the folder that CONTAINS robot_hat/)
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from robot_hat import Servo  # <-- correct package import

from time import sleep

servos = [Servo(i) for i in range(12)]

while True:
    for servo in servos:
        servo.angle(-20)
        sleep(0.1)
    for servo in servos:
        servo.angle(20)
        sleep(0.1)

