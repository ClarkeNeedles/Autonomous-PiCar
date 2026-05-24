from robot_hat import Ultrasonic
from robot_hat import Pin
import time

# Initialize the ultrasonic sensor (connect to the dedicated port on the HAT)
# The library handles the specific GPIO pins for the HAT
trig = Pin("D2", 1)
echo = Pin("D3", mode=Pin.IN, pull=Pin.PULL_DOWN)
ultrasonic = Ultrasonic(trig, echo)

try:
    while True:
        distance = ultrasonic.read() # Get distance in cm
        print(f"Distance: {distance} cm")
        time.sleep(0.1) # Small delay to prevent overloading the processor

except KeyboardInterrupt:
    # Stop the program with Ctrl+C
    print("Program stopped by user")
