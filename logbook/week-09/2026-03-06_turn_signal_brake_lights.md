---
title: Turn Signal and Brake Light Implementation
date: 2026-03-06
week: 09
authors: [Jimmy Moutafis-Tymcio, Clarke Needles, Ben Malvern, Filip Radenovic]
hours: 3.5
status: Completed
tags: [hardware, electronics, LEDs, PWM, GPIO, signals, safety-features]
---

## 1. Objective

To implement turn signal and brake light functionality for the PiCar-X, including software detection of turning and stopping maneuvers and physical LED circuit construction using available GPIO pins.

## 2. Work Summary

### Hardware Implementation

**LED Circuit Construction:**
- Designed and built physical circuit for vehicle signaling system
- **Turn Signals**: 2 LEDs (left and right indicators)
- **Brake Lights**: 2 LEDs (rear brake indicators)
- Included appropriate current-limiting resistors for LED protection

**Pin Assignment Strategy:**
- **Challenge**: Insufficient available digital GPIO pins for all LED outputs
- **Solution**: Utilized PWM (Pulse Width Modulation) pins instead of standard digital pins
  - PWM pins can function as digital outputs when set to 0% or 100% duty cycle
  - Allows binary on/off control despite being designed for analog output
  - Frees up limited digital pins for other critical sensors

**Circuit Specifications:**
- Each LED paired with a 220Ω current-limiting resistor to prevent burnout
- Standard forward voltage: ~2V (typical for red/yellow LEDs)
- Target current: ~20mA per LED
- Resistor calculation: $R = \frac{V_{supply} - V_{LED}}{I_{LED}} = \frac{5V - 2V}{0.02A} = 150\Omega$ (using 220Ω standard value)

### Software Implementation

**Turn Signal and Brake Light Logic:**
Updated the `cmd_vel_to_robocar` node to automatically control LEDs based on vehicle state:

**Pin Assignments:**
- `P8` → Left turn signal LED
- `P9` → Right turn signal LED  
- `P10` → Brake/stop lights (both LEDs controlled together)

**Control Logic:**
The code monitors the `/cmd_vel` topic (which contains throttle and steering commands) and activates LEDs accordingly:

1. **Brake Lights (Stop Condition)**:
   - Activate when throttle = 0 (vehicle stopped)
   - Brake lights override turn signals when stopped

2. **Turn Signals (While Moving)**:
   - **Left Turn**: `angular.z > 0` → Left LED on, others off
   - **Right Turn**: `angular.z < 0` → Right LED on, others off
   - **Straight**: `angular.z = 0` → All LEDs off

3. **Priority System**:
   - Stop state takes priority over steering
   - When stopped, only brake lights illuminate regardless of steering input
   - Turn signals only active when vehicle is moving

**Implementation Approach:**
```python
# Simplified logic from actual code
def set_motors(self, throttle_percent):
    if throttle_percent == 0:
        self._is_stopped = True
        # Turn on brake lights only
        self._set_leds(left=False, right=False, stop=True)
    else:
        self._is_stopped = False
        # Motor control continues...

def set_steering(self, steering_value):
    # Only change turn signals if not stopped
    if not self._is_stopped:
        if steering_value > 0:
            self._set_leds(left=True, right=False, stop=False)
        elif steering_value < 0:
            self._set_leds(left=False, right=True, stop=False)
        else:
            self._all_leds_off()
    # Servo control continues...
```

**PWM Control:**
LEDs controlled using `pulse_width_percent()` function:
- 100% duty cycle = LED fully on
- 0% duty cycle = LED off
- Binary on/off operation (no dimming)

## 3. Design Decisions & Technical Rationale

### 3.1 Why PWM Pins for Digital Outputs?

**Problem**: Limited digital GPIO pins available on Raspberry Pi after allocating pins for motors, servos, and sensors.

**Solution**: Use PWM pins (P8, P9, P10) configured for binary operation
- Set to 100% duty cycle = LED on
- Set to 0% duty cycle = LED off
- No additional hardware required

### 3.2 LED Control Logic

**State-Based Approach**:
The system uses vehicle state (stopped vs. moving, steering direction) to determine LED output:

1. **Stop Priority**: When vehicle is stopped, only brake lights activate regardless of steering input
2. **Turn Signal Activation**: Turn signals only work when vehicle is moving
3. **Mutual Exclusivity**: Only one LED state active at a time (left OR right OR stop OR all off)

**Why This Design?**:
- Matches real vehicle behavior (brake lights override turn signals when stopping)
- Simple logic reduces bugs
- Clear visual feedback for vehicle state

## 4. Testing & Validation

**Functionality Tests Performed**:
1. ✅ **Turn Signal Test**: Verified LEDs activate correctly when steering left/right
2. ✅ **Brake Light Test**: Confirmed activation during deceleration and stopping
3. ✅ **Pin Conflict Test**: Ensured no interference with existing motor/servo PWM channels
4. ✅ **Circuit Integrity Test**: Checked resistor values prevent LED overcurrent

**Outstanding Validation**:
- [ ] Test signal visibility under various lighting conditions
- [ ] Verify signal timing is perceptible to human observers (or other vehicles)
- [ ] Integration test with full autonomous navigation stack

## 5. Challenges & Solutions

**Challenge: GPIO Pin Availability**
- **Issue**: Not enough digital GPIO pins available for all LED outputs
- **Solution**: Used PWM pins (P8, P9, P10) configured for binary on/off operation
- **Outcome**: Successfully controlled 4 LEDs (left turn, right turn, 2x brake lights) using 3 PWM pins

**Implementation Notes**:
- The brake lights share one pin (P10) since they always activate together
- Turn signals use separate pins for independent left/right control
- All LED control integrated into existing `cmd_vel_to_robocar` node without requiring separate ROS node

## 6. Future Enhancements

1. **Blinking Turn Signals**:
   - Implement 1-2 Hz blinking pattern for improved visibility
   - Use ROS timers or asyncio for non-blocking LED toggle

2. **Hazard Lights**:
   - Add emergency hazard mode (all 4 LEDs blinking)
   - Triggered by collision detection or manual override

3. **Brightness Control**:
   - Utilize PWM analog capability for daytime dimming (if pin availability improves)
   - Reduce power consumption and LED wear

4. **Integration with Traffic Rules**:
   - Activate turn signals in advance of planned turns (based on pathfinding output)
   - Hold signal for minimum duration per traffic regulations

## 7. Bill of Materials

| Component | Quantity | Specification | Purpose |
|-----------|----------|---------------|---------|
| Red LEDs | 2 | 5mm, ~2V forward voltage | Brake lights |
| Yellow/Amber LEDs | 2 | 5mm, ~2V forward voltage | Turn signals |
| Resistors | 4 | 220Ω, 1/4W | Current limiting |
| Breadboard | 1 | Mini breadboard | Circuit prototyping |

## 8. Notes & Reflections

**Team Collaboration**:
This was a successful cross-functional task combining hardware assembly with software integration. The circuit construction went smoothly, and the code integration required minimal debugging.

**Safety Feature Importance**:
Adding turn signals and brake lights significantly improves the vehicle's compliance with traffic safety norms. Even in a controlled environment like Quackston, signaling intent makes the car's behavior more predictable to observers and other autonomous agents.

**Next Steps**:
With basic signaling implemented, we should consider adding the blinking functionality in the next sprint. This would align our implementation more closely with real-world vehicle standards and improve visibility during demonstrations.

## 9. Supporting Documentation

### Images (To Be Added)
- **turn-signal-brake-light-circuit.jpg**: Breadboard layout showing LED and resistor connections
- **led-activation-test.jpg**: Photo of LEDs illuminated during testing

### Code References
- Modified node: `cmd_vel_to_robocar.py`
- LED control methods: `_set_leds()`, `set_motors()`, `set_steering()`
- Pin configuration: P8 (left), P9 (right), P10 (stop)

### External References
- Raspberry Pi GPIO Pinout: https://pinout.xyz/
- PWM Control Documentation: https://docs.ros.org/en/humble/
- LED Circuit Design: https://www.electronics-tutorials.ws/blog/led-circuit-design.html
