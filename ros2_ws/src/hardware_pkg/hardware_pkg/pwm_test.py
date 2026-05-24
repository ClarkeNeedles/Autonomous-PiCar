from robot_hat.pwm import PWM
import time

p = PWM("P8")

while True:
    for i in range(1,100):
        p.pulse_width_percent(i)
        time.sleep(0.1)