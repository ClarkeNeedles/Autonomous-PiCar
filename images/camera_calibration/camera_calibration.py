#!/usr/bin/env python3

"""
camera_calibration.py
Performs camera calibration using chessboard images in the same directory.

Outputs:
- camera_calibration.json
- debug_*.jpg (annotated images)
- chessboard_3d_positions.png
"""

__author__ = "Matthew Pan"
__copyright__ = "Copyright 2024"

import os
import cv2
import numpy as np
import glob
import json

# Force matplotlib to use headless backend BEFORE pyplot import
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ----------------------------
# Helper for JSON serialization
# ----------------------------
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# ----------------------------
# Chessboard configuration
# ----------------------------
CHESSBOARD = (6, 8)  # (columns, rows) of inner corners
criteria = (
    cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
    30,
    0.001
)

# ----------------------------
# Prepare object points
# ----------------------------
objp = np.zeros((CHESSBOARD[0] * CHESSBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHESSBOARD[0], 0:CHESSBOARD[1]].T.reshape(-1, 2)

obj_points = []  # 3D points in real world
img_points = []  # 2D points in image plane

# ----------------------------
# Load images
# ----------------------------
images = glob.glob('*.jpg')

if len(images) == 0:
    raise RuntimeError("No .jpg images found in directory")

print(f"Found {len(images)} images")

gray = None

for fname in images:
    print(f"Processing {fname}")
    img = cv2.imread(fname)

    if img is None:
        print(f"⚠️ Could not read {fname}, skipping")
        continue

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    ret, corners = cv2.findChessboardCorners(gray, CHESSBOARD, None)

    if ret:
        obj_points.append(objp)

        corners2 = cv2.cornerSubPix(
            gray, corners, (11, 11), (-1, -1), criteria
        )
        img_points.append(corners2)

        # Save debug image instead of displaying
        cv2.drawChessboardCorners(img, CHESSBOARD, corners2, ret)
        cv2.imwrite(f'debug_{fname}', img)
    else:
        print(f"❌ Chessboard not found in {fname}")
        try:
            os.remove(fname)
        except OSError as e:
            print(f"⚠️ Failed to delete {fname}: {e}")

# ----------------------------
# Camera calibration
# ----------------------------
if len(obj_points) < 3:
    raise RuntimeError("Not enough valid calibration images")

ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
    obj_points,
    img_points,
    gray.shape[::-1],
    None,
    None
)

# ----------------------------
# Reprojection error
# ----------------------------
mean_error = 0.0
for i in range(len(obj_points)):
    img_points_2, _ = cv2.projectPoints(
        obj_points[i], rvecs[i], tvecs[i], K, dist
    )
    error = cv2.norm(
        img_points[i], img_points_2, cv2.NORM_L2
    ) / len(img_points_2)
    mean_error += error

rep_error = mean_error / len(obj_points)

# ----------------------------
# Print results
# ----------------------------
print("\n=== Calibration Results ===")
print("Intrinsic Matrix (K):\n", K)
print("Distortion Coefficients:\n", dist)
print(f"Total Re-Projection Error (pixels): {rep_error}")

# ----------------------------
# Save calibration to JSON
# ----------------------------
with open('camera_calibration.json', 'w') as f:
    json.dump(
        {
            "repError": rep_error,
            "intrinsicMatrix": K,
            "distCoeff": dist,
            "rvecs": rvecs,
            "tvecs": tvecs
        },
        f,
        cls=NumpyEncoder,
        indent=4
    )

# ----------------------------
# Plot 3D chessboard positions
# ----------------------------
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

for i, (rvec, tvec) in enumerate(zip(rvecs, tvecs)):
    R, _ = cv2.Rodrigues(rvec)
    points_3d = (R @ obj_points[i].T).T + tvec.T
    ax.scatter(
        points_3d[:, 0],
        points_3d[:, 1],
        points_3d[:, 2],
        label=f'Image {i + 1}'
    )

ax.set_title("3D Chessboard Positions")
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.legend()

plt.savefig("chessboard_3d_positions.png")
plt.close()

print("\n✅ Calibration complete")
print("Saved:")
print("- camera_calibration.json")
print("- debug_*.jpg")
print("- chessboard_3d_positions.png")
