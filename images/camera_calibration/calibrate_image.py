#!/usr/bin/env python3

import cv2 as cv
import numpy as np
import json

# ----------------------------
# Load calibration results
# ----------------------------
with open('camera_calibration.json', 'r') as f:
    calib = json.load(f)

K = np.array(calib['intrinsicMatrix'], dtype=np.float32)
dist = np.array(calib['distCoeff'], dtype=np.float32)

print(dist)

# ----------------------------
# Load image
# ----------------------------
img = cv.imread('uncalib_image.jpg')
if img is None:
    raise RuntimeError("Could not read input image")

h, w = img.shape[:2]

# ----------------------------
# Compute optimal camera matrix
# ----------------------------
newcameramtx, roi = cv.getOptimalNewCameraMatrix(K, dist, (w, h), 1, (w, h))

# ----------------------------
# Undistort image
# ----------------------------
dst = cv.undistort(img, K, dist, None, newcameramtx)

# ----------------------------
# Crop image (optional)
# ----------------------------
x, y, w, h = roi
dst = dst[y:y+h, x:x+w]

# ----------------------------
# Save result
# ----------------------------
cv.imwrite('calibresult.png', dst)

print("✅ Undistorted image saved as calibresult.png")
