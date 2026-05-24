import subprocess
import numpy as np
import cv2

W, H = 1920, 1080
FPS = 30

cmd = [
    "rpicam-vid",
    "-t", "0",
    "--codec", "mjpeg",
    "--width", str(W),
    "--height", str(H),
    "--framerate", str(FPS),
    "--nopreview",
    "-o", "-"
]

proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter("output.mp4", fourcc, FPS, (W, H))

buf = b""

try:
    while True:
        chunk = proc.stdout.read(4096)
        if not chunk:
            break
        buf += chunk

        # 🔥 Process ALL complete JPEGs in buffer
        while True:
            start = buf.find(b"\xff\xd8")
            end = buf.find(b"\xff\xd9")

            if start != -1 and end != -1 and end > start:
                jpg = buf[start:end+2]
                buf = buf[end+2:]

                frame = cv2.imdecode(
                    np.frombuffer(jpg, dtype=np.uint8),
                    cv2.IMREAD_COLOR
                )

                if frame is not None:
                    out.write(frame)
            else:
                break

except KeyboardInterrupt:
    pass
finally:
    out.release()
    proc.terminate()
    print("Saved output.mp4")
