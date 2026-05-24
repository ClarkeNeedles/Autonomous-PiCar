import subprocess
import time

import keyboard  # pip install keyboard

# ---------- CONFIG ----------
ROBOT = "robocar@172.20.10.3"  # or robocar@<robot_ip>
ROS_SETUP = "/opt/ros/humble/setup.bash"
REMOTE_SCRIPT = "~/elec-392-project-blekinge-12/ros2_ws/src/robocar_base/robocar_base/stdin_to_cmdvel.py"

RATE_HZ = 80.0

MAX_LIN = 0.6
MAX_ANG = 1

# Forward ramping feel
LIN_ACCEL_BASE = 0.5   # accel when far from target (m/s^2-ish)
LIN_ACCEL_MIN  = 0.6   # accel when close to target
LIN_BRAKE      = 4.0   # decel when releasing / reversing

# Turning ramping feel (still pretty responsive)
ANG_ACCEL_BASE = 8.0
ANG_ACCEL_MIN  = 2.0
ANG_BRAKE      = 14.0
# ----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def send(ssh, lin_v, ang_v, en):
    if ssh.poll() is not None:
        raise BrokenPipeError("SSH connection closed")
    ssh.stdin.write(f"{lin_v:.3f} {ang_v:.3f} {en}\n")
    ssh.stdin.flush()

def eased_ramp(current, target, dt, accel_base, accel_min):
    """
    Ease-out ramp: big steps when far, small steps when close.
    """
    err = target - current
    a = accel_min + (accel_base - accel_min) * clamp(abs(err) / (abs(target) + 1e-6 if target != 0 else 1.0), 0.0, 1.0)
    max_delta = a * dt
    if abs(err) <= max_delta:
        return target
    return current + (max_delta if err > 0 else -max_delta)

def brake_to_zero(current, dt, brake_rate):
    """
    Stronger pull to zero when released.
    """
    max_delta = brake_rate * dt
    if abs(current) <= max_delta:
        return 0.0
    return current - (max_delta if current > 0 else -max_delta)

remote_cmd = f"bash -lc 'source {ROS_SETUP}; python3 {REMOTE_SCRIPT}'"
ssh_cmd = ["ssh", "-tt", ROBOT, remote_cmd]

print("Connecting to robot via SSH...")
ssh = subprocess.Popen(
    ssh_cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    text=True,
    bufsize=1,
)

time.sleep(0.8)
if ssh.poll() is not None:
    print("SSH exited immediately. Check network/credentials/remote script path.")
    raise SystemExit(1)

print("\nControls (smooth + better forward ramp):")
print("  Hold W/S = forward/back (eased ramp)")
print("  Hold A/D = left/right (eased ramp)")
print("  SPACE    = stop")
print("  E        = toggle enable")
print("  Q        = quit\n")

enable = 1
lin = 0.0
ang = 0.0

period = 1.0 / RATE_HZ
prev = time.time()
e_was_down = False

try:
    while True:
        now = time.time()
        dt = now - prev
        prev = now

        if keyboard.is_pressed("q"):
            break

        # toggle enable on key-down edge
        e_down = keyboard.is_pressed("e")
        if e_down and not e_was_down:
            enable = 0 if enable else 1
            print(f"enable = {enable}")
        e_was_down = e_down

        # hard stop
        if keyboard.is_pressed("space"):
            lin = 0.0
            ang = 0.0
            send(ssh, 0.0, 0.0, 0 if not enable else 1)
            time.sleep(0.02)
            continue

        # targets from true key states
        target_lin = 0.0
        target_ang = 0.0

        if keyboard.is_pressed("w"):
            target_lin += MAX_LIN
        if keyboard.is_pressed("s"):
            target_lin -= MAX_LIN

        if keyboard.is_pressed("a"):
            target_ang += MAX_ANG
        if keyboard.is_pressed("d"):
            target_ang -= MAX_ANG

        # ----- LINEAR: eased ramp + strong braking when released -----
        if target_lin == 0.0:
            lin = brake_to_zero(lin, dt, LIN_BRAKE)
        else:
            lin = eased_ramp(lin, target_lin, dt, LIN_ACCEL_BASE, LIN_ACCEL_MIN)

        # ----- ANGULAR: eased ramp + strong braking when released -----
        if target_ang == 0.0:
            ang = brake_to_zero(ang, dt, ANG_BRAKE)
        else:
            ang = eased_ramp(ang, target_ang, dt, ANG_ACCEL_BASE, ANG_ACCEL_MIN)

        lin = clamp(lin, -MAX_LIN, MAX_LIN)
        ang = clamp(ang, -MAX_ANG, MAX_ANG)

        if enable:
            send(ssh, lin, ang, 1)
        else:
            send(ssh, 0.0, 0.0, 0)

        sleep_t = period - (time.time() - now)
        if sleep_t > 0:
            time.sleep(sleep_t)

except KeyboardInterrupt:
    pass
except Exception as e:
    print(f"Controller stopped: {e}")

print("Done.")
