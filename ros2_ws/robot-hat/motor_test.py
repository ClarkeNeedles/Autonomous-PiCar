import time

# IMPORTANT: import Motors directly to avoid audio / music imports
from robot_hat.motor import Motors

motors = Motors()

SPEED = 25  # start low

try:
    print("Motor 1 forward")
    motors[1].speed(SPEED)
    motors[2].speed(0)
    time.sleep(1.5)

    print("Motor 2 forward")
    motors[1].speed(0)
    motors[2].speed(SPEED)
    time.sleep(1.5)

    print("Both motors forward")
    motors[1].speed(SPEED)
    motors[2].speed(SPEED)
    time.sleep(2)

    print("Reverse both motors")
    motors[1].speed(-SPEED)
    motors[2].speed(-SPEED)
    time.sleep(2)

    print("Stop")
    motors.stop()

except KeyboardInterrupt:
    print("\nEmergency stop")
    motors.stop()
