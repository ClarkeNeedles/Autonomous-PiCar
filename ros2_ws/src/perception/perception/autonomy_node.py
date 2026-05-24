#!/usr/bin/env python3

import os
import time
import numpy as np
import cv2
from collections import deque
from datetime import datetime
from enum import Enum

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from std_msgs.msg import String, Int32MultiArray, Bool
from cv_bridge import CvBridge

# Turn codes matching mapping.cpp TurnCode enum
TURN_LEFT     = 0
TURN_STRAIGHT = 1
TURN_RIGHT    = 2


class State(Enum):
    LINE_FOLLOWING      = 'LINE_FOLLOWING'
    CROSSING_FIRST      = 'CROSSING_FIRST'    # driving through first cross-lane before a left turn
    TURNING_RIGHT       = 'TURNING_RIGHT'
    TURNING_LEFT        = 'TURNING_LEFT'
    TANK_TURNING_LEFT   = 'TANK_TURNING_LEFT'
    TANK_TURNING_RIGHT  = 'TANK_TURNING_RIGHT'
    PRE_TURN            = 'PRE_TURN'              # drive straight briefly before tank turn
    STOPPING            = 'STOPPING'
    LINE_LOST           = 'LINE_LOST'


class AutonomyNode(Node):
    def __init__(self):
        super().__init__('autonomy_node')

        # --- Parameters ---
        self.declare_parameter('speed',      0.4)
        self.declare_parameter('turn_speed', 0.3)
        # PD gains
        self.declare_parameter('kp', 0.8)
        self.declare_parameter('kd', 0.3)
        # Smoothing / noise tolerance
        self.declare_parameter('alpha',            0.35)  # error low-pass  (0=frozen, 1=raw)
        self.declare_parameter('steer_alpha',      0.40)  # output low-pass
        self.declare_parameter('steer_rate_limit', 0.12)  # max steer change per frame (normalised)
        self.declare_parameter('jump_threshold',   0.45)  # reject error jumps larger than this
        # Confidence / adaptive speed
        self.declare_parameter('confidence_speed_factor', 0.5)  # speed reduction at zero confidence
        self.declare_parameter('coast_duration',          0.4)  # seconds to coast before LINE_LOST
        # Intersection / blob gates
        self.declare_parameter('min_blob_area',   300)
        self.declare_parameter('min_follow_area', 2000)
        # Controller misc
        self.declare_parameter('steering_deadband',       0.03)
        self.declare_parameter('steering_gain',           1.0)
        self.declare_parameter('max_line_follow_angular', 1.0)
        # Mask pre-processing
        self.declare_parameter('green_morph_kernel',    5)
        self.declare_parameter('mask_top_crop_percent', 25)
        # Line-lost recovery
        self.declare_parameter('line_lost_reverse_speed',    -0.2)
        self.declare_parameter('line_lost_reverse_duration',  2.0)
        # Tank turn at intersection
        self.declare_parameter('tank_turn_angular_speed',  0.12)   # angular.z sent during tank turn (350*0.12 ≈ 42% motor)
        self.declare_parameter('tank_turn_min_green',      3000)   # green pixels needed to confirm lane acquired
        self.declare_parameter('tank_turn_confirm_frames', 4)      # consecutive frames required
        self.declare_parameter('tank_turn_timeout',        6.0)    # safety timeout (seconds)
        self.declare_parameter('pre_turn_drive_duration',  0.3)   # seconds to drive straight after cross-line before tank turn
        self.declare_parameter('post_turn_cooldown',        2.0)   # seconds to ignore cross/yellow detection after a tank turn
        self.declare_parameter('post_turn_min_confidence', 0.5)   # minimum confidence required to drive during post-turn cooldown
        self.declare_parameter('tank_turn_exit_center',    0.35)  # max centroid offset (0=center,1=edge) to exit tank turn
        # Detection thresholds
        self.declare_parameter('cross_min_width_pct',   0.55)  # p10-p90 green spread required to count as a cross-lane (0-1)
        self.declare_parameter('yellow_stop_threshold', 200)   # yellow pixels needed to trigger stop
        self.declare_parameter('yellow_stop_duration',  0.5)   # seconds to hold stopped at yellow line
        self.declare_parameter('green_bottom_threshold', 50)   # green pixels needed in bottom to confirm line
        # Route
        self.declare_parameter('route', 'STRAIGHT,STRAIGHT,STRAIGHT')
        # Debug video recording
        self.declare_parameter('record_debug_video', False)
        self.declare_parameter('video_output_dir', os.path.expanduser('~/recordings'))
        self.declare_parameter('video_fps', 30)

        self.speed                       = float(self.get_parameter('speed').value)
        self.turn_speed                  = float(self.get_parameter('turn_speed').value)
        self.kp                          = float(self.get_parameter('kp').value)
        self.kd                          = float(self.get_parameter('kd').value)
        self.alpha                       = max(0.0, min(1.0, float(self.get_parameter('alpha').value)))
        self.steer_alpha                 = max(0.0, min(1.0, float(self.get_parameter('steer_alpha').value)))
        self.steer_rate_limit            = max(0.0, float(self.get_parameter('steer_rate_limit').value))
        self.jump_threshold              = max(0.01, float(self.get_parameter('jump_threshold').value))
        self.confidence_speed_factor     = max(0.0, min(1.0, float(self.get_parameter('confidence_speed_factor').value)))
        self.coast_duration              = max(0.0, float(self.get_parameter('coast_duration').value))
        self.min_blob_area               = int(self.get_parameter('min_blob_area').value)
        self.min_follow_area             = int(self.get_parameter('min_follow_area').value)
        self.steering_deadband           = max(0.0, float(self.get_parameter('steering_deadband').value))
        self.steering_gain               = max(0.0, float(self.get_parameter('steering_gain').value))
        self.max_line_follow_angular     = max(0.0, float(self.get_parameter('max_line_follow_angular').value))
        self.green_morph_kernel          = max(1, int(self.get_parameter('green_morph_kernel').value))
        self.mask_top_crop_percent       = max(0, min(100, int(self.get_parameter('mask_top_crop_percent').value)))
        self.line_lost_reverse_speed     = float(self.get_parameter('line_lost_reverse_speed').value)
        self.line_lost_reverse_duration  = max(0.0, float(self.get_parameter('line_lost_reverse_duration').value))
        self.tank_turn_angular_speed     = max(0.0, float(self.get_parameter('tank_turn_angular_speed').value))
        self.tank_turn_min_green         = int(self.get_parameter('tank_turn_min_green').value)
        self.tank_turn_confirm_frames    = max(1, int(self.get_parameter('tank_turn_confirm_frames').value))
        self.tank_turn_timeout           = max(0.0, float(self.get_parameter('tank_turn_timeout').value))
        self.pre_turn_drive_duration     = max(0.0, float(self.get_parameter('pre_turn_drive_duration').value))
        self.post_turn_cooldown          = max(0.0, float(self.get_parameter('post_turn_cooldown').value))
        self.post_turn_min_confidence    = max(0.0, float(self.get_parameter('post_turn_min_confidence').value))
        self.tank_turn_exit_center       = max(0.0, float(self.get_parameter('tank_turn_exit_center').value))
        self.cross_min_width_pct         = float(self.get_parameter('cross_min_width_pct').value)
        self.yellow_stop_threshold       = int(self.get_parameter('yellow_stop_threshold').value)
        self.yellow_stop_duration        = float(self.get_parameter('yellow_stop_duration').value)
        self.green_bottom_threshold      = int(self.get_parameter('green_bottom_threshold').value)

        route_str = str(self.get_parameter('route').value)
        shorthand = {'S': 'STRAIGHT', 'L': 'LEFT', 'R': 'RIGHT'}
        self.route_queue = deque(
            shorthand.get(s.strip().upper(), s.strip().upper()) for s in route_str.split(',')
        )

        # Debug video writer
        self.debug_video_writer = None
        if bool(self.get_parameter('record_debug_video').value):
            video_dir = str(self.get_parameter('video_output_dir').value)
            video_fps = int(self.get_parameter('video_fps').value)
            os.makedirs(video_dir, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            video_path = os.path.join(video_dir, f'autonomy_{ts}.mp4')
            self.debug_video_writer = cv2.VideoWriter(
                video_path,
                cv2.VideoWriter_fourcc(*'mp4v'),
                video_fps,
                (256, 256),
            )
            self.get_logger().info(f'Recording autonomy debug video to {video_path}')

        self.next_direction = None
        self.turn_queue     = deque()
        self.create_subscription(String, '/next_direction', self._on_next_direction, 10)
        self.create_subscription(Int32MultiArray, '/navigation/turn_queue', self._on_turn_queue, 10)

        # State machine
        self.state            = State.LINE_FOLLOWING
        self.state_entry_time = time.time()

        # Filtered control state
        self.error_filtered      = 0.0   # low-passed error (P source)
        self.prev_error_filtered = 0.0   # one frame ago    (D source)
        self.steer_filtered      = 0.0   # low-passed output
        self.ever_had_valid      = False
        self.last_valid_time     = time.time()

        # Debug overlay: raw centroid pixel column
        self.centroid_px = None

        # Temporal smoothing buffers
        self.yellow_history = deque(maxlen=2)

        # Line-lost recovery
        self.line_lost_angular = 0.0

        # Pending turn action (set when first cross-line fires, consumed on second or tank turn)
        self.pending_turn_action  = None
        self.pre_turn_direction   = None    # 'LEFT' or 'RIGHT' — set when entering PRE_TURN
        self.post_turn_until      = 0.0    # wall-clock time until which cross/yellow detection is suppressed

        # Counters / flags
        self.frame_counter           = 0
        self.yellow_present_frames   = 0
        self.yellow_armed            = False
        self.tank_turn_confirm_count = 0
        self.cross_confirm_count = 0      # consecutive frames with a wide green band in bottom zone
        self.cross_armed         = False  # True once bottom band confirmed — waiting for disappear
        self.cross_count_at_arm  = 0      # 1 or 2 lanes detected when armed
        self.last_cross_count    = 0      # for debug overlay

        # Publishers / subscribers
        self.cmd_pub         = self.create_publisher(Twist, '/cmd_vel', 10)
        self.tank_steer_pub  = self.create_publisher(Bool, '/tank_steer', 10)
        self.turn_signal_pub = self.create_publisher(String, '/turn_signal_cmd', 10)
        self.debug_pub       = self.create_publisher(Image, '/autonomy/debug_image', 1)
        self.bridge          = CvBridge()
        self.driving_allowed = True
        self.create_subscription(Image, '/segmentation/mask', self.mask_callback, 1)
        self.create_subscription(Bool, '/autonomy/driving_allowed', self._on_driving_allowed, 10)

        self.get_logger().info(
            f'AutonomyNode started | speed={self.speed} kp={self.kp} kd={self.kd} '
            f'alpha={self.alpha} steer_alpha={self.steer_alpha} route={list(self.route_queue)}'
        )

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    def set_drive_command(self, twist, speed, steer):
        twist.linear.x  = float(speed)
        twist.angular.z = float(max(-1.0, min(1.0, steer)))

    def reset_steering_filters(self):
        self.error_filtered      = 0.0
        self.prev_error_filtered = 0.0
        self.steer_filtered      = 0.0
        self.ever_had_valid      = False  # reset jump-filter reference so first new centroid is accepted

    def _on_next_direction(self, msg):
        direction = msg.data.strip().upper()
        if direction in ('LEFT', 'RIGHT', 'STRAIGHT'):
            self.next_direction = direction
            self.get_logger().info(f'Received next direction: {direction}')
        else:
            self.get_logger().warn(f'Invalid direction received: {msg.data}')

    def _on_turn_queue(self, msg):
        """Receive turn queue from /navigation/turn_queue (0=LEFT,1=STRAIGHT,2=RIGHT).

        Ignore updates while a turn maneuver is in progress OR during the post-turn
        cooldown window.  The planner continuously replans on every pose update, so
        without this guard it would re-queue the turn we just consumed before the car
        has physically cleared the intersection.
        """
        if self.state in (
            State.PRE_TURN,
            State.CROSSING_FIRST,
            State.TANK_TURNING_LEFT,
            State.TANK_TURNING_RIGHT,
        ) or time.time() < self.post_turn_until:
            return

        new_queue = deque(
            v for v in msg.data if v in (TURN_LEFT, TURN_STRAIGHT, TURN_RIGHT)
        )
        if new_queue != self.turn_queue:
            self.turn_queue = new_queue
            self.get_logger().info(f'Turn queue updated: {list(self.turn_queue)}')

    def _on_driving_allowed(self, msg):
        self.driving_allowed = msg.data

    def _pop_next_action(self):
        """Pop the next turn action: turn_queue > next_direction > route_queue."""
        if self.turn_queue:
            turn_code = self.turn_queue.popleft()
            return {TURN_LEFT: 'LEFT', TURN_STRAIGHT: 'STRAIGHT', TURN_RIGHT: 'RIGHT'}.get(turn_code, 'STRAIGHT')
        if self.next_direction is not None:
            action = self.next_direction
            self.next_direction = None
            return action
        if self.route_queue:
            return self.route_queue.popleft()
        self.get_logger().warn('No direction in any queue — defaulting STRAIGHT')
        return 'STRAIGHT'

    def _handle_cross_line(self, now, cross_count=1):
        """
        Called once per cross-lane detection (rising edge, state-gated).

        LINE_FOLLOWING + LEFT:
          2 cross-lines visible → CROSSING_FIRST (2-way road, skip first lane then turn)
          1 cross-line visible  → TANK_TURNING_LEFT immediately (1-way road)
        LINE_FOLLOWING + RIGHT  → TANK_TURNING_RIGHT immediately
        LINE_FOLLOWING + STRAIGHT → keep following

        CROSSING_FIRST → TANK_TURNING_LEFT (second cross-line reached)
        """
        if self.state == State.LINE_FOLLOWING:
            action = self._pop_next_action()
            self.pending_turn_action = action
            self.reset_steering_filters()

            if action == 'LEFT':
                if cross_count >= 2:
                    # 2-way road: drive through first lane, turn on second
                    self.state = State.CROSSING_FIRST
                    self.state_entry_time = now
                    self.get_logger().info(
                        f'Cross-line ({cross_count} lanes) + LEFT → CROSSING_FIRST')
                else:
                    # 1-way road: coast over line then tank turn
                    self.state = State.PRE_TURN
                    self.pre_turn_direction = 'LEFT'
                    self.state_entry_time = now
                    self.get_logger().info('Cross-line (1 lane) + LEFT → PRE_TURN → TANK_TURNING_LEFT')
            elif action == 'RIGHT':
                self.state = State.PRE_TURN
                self.pre_turn_direction = 'RIGHT'
                self.state_entry_time = now
                self.get_logger().info('Cross-line → PRE_TURN → TANK_TURNING_RIGHT')
            else:  # STRAIGHT
                if cross_count >= 2:
                    # 2-way road: must absorb the second cross-line without popping again
                    self.state = State.CROSSING_FIRST
                    self.state_entry_time = now
                    self.get_logger().info(
                        f'Cross-line ({cross_count} lanes) + STRAIGHT → CROSSING_FIRST (absorb 2nd)')
                # else 1-way + STRAIGHT: nothing to do, stay in LINE_FOLLOWING

        elif self.state == State.CROSSING_FIRST:
            # Second cross-line — action was already popped on the first
            if self.pending_turn_action == 'LEFT':
                self.state = State.PRE_TURN
                self.pre_turn_direction = 'LEFT'
                self.state_entry_time = now
                self.reset_steering_filters()
                self.get_logger().info('Cross-line 2 → PRE_TURN → TANK_TURNING_LEFT')
            else:
                # STRAIGHT: second line absorbed, resume following
                self.state = State.LINE_FOLLOWING
                self.state_entry_time = now
                self.reset_steering_filters()
                self.get_logger().info('Cross-line 2 (STRAIGHT) → LINE_FOLLOWING')

    def _set_tank_steer(self, enabled: bool):
        """Publish to /tank_steer to switch cmd_vel_to_robocar between Ackermann and tank modes."""
        msg = Bool()
        msg.data = enabled
        self.tank_steer_pub.publish(msg)

    def publish_turn_signal(self):
        msg = String()

        if self.state in {State.TURNING_LEFT, State.TANK_TURNING_LEFT}:
            msg.data = "LEFT"
        elif self.state in {State.TURNING_RIGHT, State.TANK_TURNING_RIGHT}:
            msg.data = "RIGHT"
        elif self.state == State.CROSSING_FIRST and self.pending_turn_action == "LEFT":
            msg.data = "LEFT"
        elif self.state == State.CROSSING_FIRST and self.pending_turn_action == "RIGHT":
            msg.data = "RIGHT"
        else:
            msg.data = "NONE"

        self.turn_signal_pub.publish(msg)

    # ------------------------------------------------------------------
    #  Mask cleaning
    # ------------------------------------------------------------------

    def clean_mask(self, mask):
        """Crop top N%, denoise, keep the single best line blob."""
        h, w = mask.shape
        cleaned = mask.copy()
        crop_rows = int(h * self.mask_top_crop_percent / 100.0)
        cleaned[:crop_rows, :] = 0

        green_binary = (cleaned == 1).astype(np.uint8)
        if self.green_morph_kernel > 1:
            kernel = np.ones((self.green_morph_kernel, self.green_morph_kernel), dtype=np.uint8)
            green_binary = cv2.morphologyEx(green_binary, cv2.MORPH_OPEN,  kernel)
            green_binary = cv2.morphologyEx(green_binary, cv2.MORPH_CLOSE, kernel)

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            green_binary, connectivity=8
        )

        if num_labels <= 1:
            cleaned[cleaned == 1] = 0
            return cleaned

        areas    = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
        max_area = max(areas) if areas else 1

        # Count blobs above min_blob_area — if ≥2 we're at an intersection with multiple lanes
        valid_blobs = [i for i in range(1, num_labels) if stats[i, cv2.CC_STAT_AREA] >= self.min_blob_area]
        multi_lane  = len(valid_blobs) >= 2

        best_score = -1.0
        best_label = -1
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < self.min_blob_area:
                continue
            norm_area        = area / max_area
            center_proximity = 1.0 - min(abs(centroids[i][0] - w / 2.0) / (w / 2.0), 1.0)
            bottom_reach     = (stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT]) / float(h)
            if multi_lane:
                # Left-lane preference at intersections: on 2-lane roads always take the left lane.
                # A blob further left (smaller centroid_x) gets a higher left_preference score.
                left_preference = 1.0 - (centroids[i][0] / w)
                score = 0.35 * norm_area + 0.25 * center_proximity + 0.15 * bottom_reach + 0.25 * left_preference
            else:
                # Single lane: original weights, no left bias to avoid steering distortion
                score = 0.40 * norm_area + 0.40 * center_proximity + 0.20 * bottom_reach
            if score > best_score:
                best_score = score
                best_label = i

        if best_label == -1:
            cleaned[cleaned == 1] = 0
            return cleaned

        best_blob = labels == best_label
        cleaned[cleaned == 1] = 0
        cleaned[best_blob] = 1
        return cleaned

    # ------------------------------------------------------------------
    #  Steering error extraction  (bottom 60% of mask)
    # ------------------------------------------------------------------

    def _zone_centroid(self, mask, row_start, row_end, min_cols=20):
        cols = np.where(mask[row_start:row_end] == 1)[1]
        if len(cols) < min_cols:
            return None
        return float(np.mean(cols))

    def _extract_error(self, mask):
        """
        Compute lateral error from the bottom 60% of the mask.
        Falls back to full mask if bottom zone is empty.
        Returns (raw_error, confidence) or (None, 0.0) if rejected.
        """
        h, w   = mask.shape
        near_start = int(h * 0.40)  # bottom 60%

        centroid = self._zone_centroid(mask, near_start, h)
        if centroid is None:
            centroid = self._zone_centroid(mask, 0, h)  # full-mask fallback

        self.centroid_px = int(centroid) if centroid is not None else None

        if centroid is None:
            return None, 0.0

        raw = self.steering_gain * (centroid - w / 2.0) / (w / 2.0)
        raw = max(-1.0, min(1.0, raw))

        # If the jump is too large, creep toward the new value slowly instead of
        # hard-rejecting.  Hard rejection causes a lock-up: filtered never updates,
        # so every subsequent real frame also looks like a "jump" and stays rejected.
        if self.ever_had_valid and abs(raw - self.error_filtered) > self.jump_threshold:
            self.error_filtered += 0.05 * (raw - self.error_filtered)
            return None, 0.0

        # Confidence: total green pixels vs expected minimum
        green_count = int(np.count_nonzero(mask == 1))
        confidence  = min(1.0, green_count / max(1, self.min_follow_area * 3.0))

        return raw, confidence

    # ------------------------------------------------------------------
    #  Intersection / yellow / turn helpers
    # ------------------------------------------------------------------

    def _line_in_bottom(self, mask, require_centered=False, center_margin=0.35):
        """
        Check if green in bottom 15% forms a coherent line (not too wide, not too sparse).
        If require_centered=True, also check that the line centroid is within center_margin
        of the frame center (0.0 = exact center, 1.0 = edge), ensuring the car is aligned.
        """
        h, w = mask.shape
        bottom_start = int(h * 0.85)
        bottom = mask[bottom_start:]
        green_cols = np.where(bottom == 1)[1]
        if len(green_cols) < self.green_bottom_threshold * 2:
            return False
        # Width of green band — a line should be narrow, not spanning the whole frame
        width = float(np.max(green_cols) - np.min(green_cols))
        width_pct = width / w
        # A line is roughly 10-50% of frame width; an intersection is wider
        if not (0.05 < width_pct < 0.55):
            return False
        if require_centered:
            centroid_x = float(np.mean(green_cols))
            offset = abs(centroid_x - w / 2.0) / (w / 2.0)
            return offset <= center_margin
        return True

    def get_turn_completion_angle(self, mask):
        h = mask.shape[0]
        bottom_mask = mask.copy()
        bottom_mask[:h // 2, :] = 0
        rows, cols = np.where(bottom_mask == 1)
        if len(rows) < 100:
            return None
        try:
            coeffs = np.polyfit(rows, cols, 1)
            return float(np.degrees(np.arctan(coeffs[0])))
        except Exception:
            return None

    def _green_cross_in_zone(self, mask, row_start_pct, row_end_pct, min_width_pct=0.55):
        """
        Return True if a wide horizontal green band (cross-lane) is present in the
        given row range.  Uses the 10th-90th percentile column spread of green pixels
        to be robust against sparse noise at the edges.

        A cross-lane spans most of the frame width; the forward driving lane is narrow,
        so min_width_pct=0.55 cleanly separates them.
        """
        h, w = mask.shape
        region = mask[int(h * row_start_pct):int(h * row_end_pct), :]
        green_cols = np.where(region == 1)[1]
        if len(green_cols) < 20:
            return False
        p10 = np.percentile(green_cols, 10)
        p90 = np.percentile(green_cols, 90)
        return (p90 - p10) / w >= min_width_pct

    def yellow_in_bottom(self, mask):
        h, w = mask.shape
        row_start = int(h * 0.65)
        row_end   = int(h * 0.90)
        col_start = int(w * 0.15)
        col_end   = int(w * 0.85)
        region = mask[row_start:row_end, col_start:col_end]
        yellow_rows = np.where(region == 2)[0]
        if len(yellow_rows) < self.yellow_stop_threshold:
            return False
        # Reject large floor fills: real stop lines span < 70% of the search zone height.
        # The full search zone is ~64px; a floor fill spans nearly all of it (~63px),
        # while a stop line seen up close is typically ≤ 44px tall.
        row_span = int(yellow_rows.max()) - int(yellow_rows.min())
        max_span = int((row_end - row_start) * 0.70)
        return row_span <= max_span

    # ------------------------------------------------------------------
    #  Main callback
    # ------------------------------------------------------------------

    def mask_callback(self, msg):
        try:
            raw_mask = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width)
        except Exception as e:
            self.get_logger().warn(f'Bad mask frame: {e}')
            return

        # Clean mask for steering: selects the single best lane blob
        mask = self.clean_mask(raw_mask)

        now = time.time()
        in_cooldown = now < self.post_turn_until
        yellow_now = (not in_cooldown) and self.yellow_in_bottom(mask)
        self.yellow_history.append(yellow_now)
        if yellow_now:
            self.yellow_present_frames += 1
            if self.yellow_present_frames >= 5:
                self.yellow_armed = True
        else:
            if in_cooldown:
                self.yellow_present_frames = 0
                self.yellow_armed = False
            else:
                self.yellow_present_frames = 0

        green_count = int(np.count_nonzero(mask == 1))

        # --- Error extraction ---
        raw_error, confidence = self._extract_error(mask)

        if raw_error is not None:
            # Low-pass filter the error — D is computed on the filtered signal
            self.error_filtered = (self.alpha * raw_error
                                   + (1.0 - self.alpha) * self.error_filtered)
            self.ever_had_valid  = True
            self.last_valid_time = time.time()

        twist = Twist()

        # ---- Cross-line detection (only when relevant) -------------------
        # Run Hough only in states where a cross-line should trigger a turn.
        # This avoids spurious detections during tank turns or stopping.
        # ---- Cross-lane detection (pixel-width method, same logic as yellow stop) -----
        # Bottom zone (70-95%): cross-lane present right in front of car.
        # Mid zone   (35-65%): second cross-lane further ahead — indicates 2-lane road.
        # Trigger on TRAILING EDGE: arm when line appears, fire when it disappears.
        if self.state in (State.LINE_FOLLOWING, State.CROSSING_FIRST) and not in_cooldown:
            cross_in_bottom = self._green_cross_in_zone(raw_mask, 0.70, 0.95, self.cross_min_width_pct)
            if cross_in_bottom:
                self.cross_confirm_count += 1
                if self.cross_confirm_count >= 3 and not self.cross_armed:
                    # Check for a second cross-lane further ahead (2-lane road)
                    cross_in_mid = self._green_cross_in_zone(raw_mask, 0.35, 0.65, self.cross_min_width_pct)
                    self.cross_count_at_arm = 2 if cross_in_mid else 1
                    self.cross_armed    = True
                    self.last_cross_count = self.cross_count_at_arm
            else:
                if self.cross_armed:
                    # Line passed under the car — execute turn now
                    self._handle_cross_line(now, self.cross_count_at_arm)
                    self.cross_armed = False
                self.cross_confirm_count = 0
        else:
            self.cross_confirm_count = 0
            self.cross_armed         = False
            self.last_cross_count    = 0

        # ---- State machine -----------------------------------------------

        if self.state == State.LINE_FOLLOWING:
            if green_count < self.min_follow_area:
                self.line_lost_angular = self.steer_filtered
                self.state            = State.LINE_LOST
                self.state_entry_time = now
                # Clear cross-lane arm so we don't phantom-fire a turn on recovery
                self.cross_armed       = False
                self.cross_confirm_count = 0
                self.get_logger().warn(
                    f'Line lost! turn_queue has {len(self.turn_queue)} pending turns'
                )

            else:
                stop_triggered = (
                    self.yellow_armed
                    and len(self.yellow_history) >= 2
                    and self.yellow_history[-2]
                    and not self.yellow_history[-1]
                )

                if stop_triggered:
                    self.yellow_armed          = False
                    self.yellow_present_frames = 0
                    self.state                 = State.STOPPING
                    self.state_entry_time      = now
                    self.reset_steering_filters()
                    self.get_logger().info('Yellow stop line passed -> STOPPING')

                else:
                    # PD on filtered error — D on filtered signal, not raw noise
                    d_error = self.error_filtered - self.prev_error_filtered
                    self.prev_error_filtered = self.error_filtered

                    steer_raw = self.kp * self.error_filtered + self.kd * d_error
                    steer_raw = max(-self.max_line_follow_angular,
                                   min( self.max_line_follow_angular, steer_raw))

                    # Rate-limit: cap per-frame change
                    delta = max(-self.steer_rate_limit,
                                min( self.steer_rate_limit, steer_raw - self.steer_filtered))
                    steer_candidate = self.steer_filtered + delta

                    # Confidence blend: hold last known when unsure
                    steer_blended = (confidence       * steer_candidate
                                     + (1.0 - confidence) * self.steer_filtered)

                    # Output low-pass
                    steer_out = (self.steer_alpha       * steer_blended
                                 + (1.0 - self.steer_alpha) * self.steer_filtered)
                    self.steer_filtered = steer_out

                    if abs(steer_out) < self.steering_deadband:
                        steer_out = 0.0

                    # Adaptive speed: slow down when confidence is low
                    speed = self.speed * (1.0 - self.confidence_speed_factor * (1.0 - confidence))
                    speed = max(self.speed * 0.3, speed)

                    self.set_drive_command(twist, speed, steer_out)

        elif self.state == State.TURNING_RIGHT:
            self.set_drive_command(twist, self.turn_speed, -1.0)
            line_angle = self.get_turn_completion_angle(mask)
            if line_angle is not None and line_angle > 25.0 and green_count >= self.min_blob_area:
                self.state            = State.LINE_FOLLOWING
                self.state_entry_time = now
                self.reset_steering_filters()
                self.get_logger().info(f'Right turn complete (angle={line_angle:.1f} deg)')

        elif self.state == State.TURNING_LEFT:
            self.set_drive_command(twist, self.turn_speed, 1.0)
            line_angle = self.get_turn_completion_angle(mask)
            if line_angle is not None and line_angle < -25.0 and green_count >= self.min_blob_area:
                self.state            = State.LINE_FOLLOWING
                self.state_entry_time = now
                self.reset_steering_filters()
                self.get_logger().info(f'Left turn complete (angle={line_angle:.1f} deg)')

        elif self.state == State.CROSSING_FIRST:
            # Drive through first cross-lane waiting for the second, using PD to stay on lane.
            # _handle_cross_line transitions to the correct state on second detection.
            # Timeout fallback in case the second line is missed.
            d_error = self.error_filtered - self.prev_error_filtered
            self.prev_error_filtered = self.error_filtered
            steer_raw = self.kp * self.error_filtered + self.kd * d_error
            steer_raw = max(-self.max_line_follow_angular, min(self.max_line_follow_angular, steer_raw))
            delta = max(-self.steer_rate_limit, min(self.steer_rate_limit, steer_raw - self.steer_filtered))
            steer_out = self.steer_filtered + delta
            self.steer_filtered = steer_out
            self.set_drive_command(twist, self.speed, steer_out)
            if now - self.state_entry_time > 3.0:
                if self.pending_turn_action == 'LEFT':
                    self.state = State.PRE_TURN
                    self.pre_turn_direction = 'LEFT'
                    self.get_logger().warn('CROSSING_FIRST timeout → PRE_TURN → TANK_TURNING_LEFT')
                else:
                    self.state = State.LINE_FOLLOWING
                    self.get_logger().warn('CROSSING_FIRST timeout → LINE_FOLLOWING')
                self.state_entry_time = now
                self.reset_steering_filters()

        elif self.state == State.PRE_TURN:
            # Drive straight over the cross-line for pre_turn_drive_duration seconds, then tank turn
            self.set_drive_command(twist, self.speed, 0.0)
            if now - self.state_entry_time >= self.pre_turn_drive_duration:
                if self.pre_turn_direction == 'LEFT':
                    self.state = State.TANK_TURNING_LEFT
                else:
                    self.state = State.TANK_TURNING_RIGHT
                self._set_tank_steer(True)
                self.state_entry_time = now
                self.reset_steering_filters()
                self.get_logger().info(f'PRE_TURN done → TANK_TURNING_{self.pre_turn_direction}')

        elif self.state == State.TANK_TURNING_LEFT:
            twist.linear.x  = 0.0
            twist.angular.z = -self.tank_turn_angular_speed
            elapsed = now - self.state_entry_time
            # Single-phase: exit as soon as the target lane appears in the very bottom of frame.
            # (No "wait for disappear" — linear.x=0 so the car never drives over the line.)
            if elapsed > 1.0 and self._line_in_bottom(mask, require_centered=True, center_margin=self.tank_turn_exit_center):
                self._set_tank_steer(False)
                self.state = State.LINE_FOLLOWING
                self.state_entry_time = now
                self.post_turn_until = now + self.post_turn_cooldown
                self.reset_steering_filters()
                self.get_logger().info('Tank LEFT complete — lane acquired (2s cooldown)')
            elif elapsed > self.tank_turn_timeout:
                self._set_tank_steer(False)
                self.state = State.LINE_FOLLOWING
                self.state_entry_time = now
                self.post_turn_until = now + self.post_turn_cooldown
                self.reset_steering_filters()
                self.get_logger().warn('Tank LEFT timeout — resuming line following (2s cooldown)')

        elif self.state == State.TANK_TURNING_RIGHT:
            twist.linear.x  = 0.0
            twist.angular.z = self.tank_turn_angular_speed
            elapsed = now - self.state_entry_time
            if elapsed > 1.0 and self._line_in_bottom(mask, require_centered=True, center_margin=self.tank_turn_exit_center):
                self._set_tank_steer(False)
                self.state = State.LINE_FOLLOWING
                self.state_entry_time = now
                self.post_turn_until = now + self.post_turn_cooldown
                self.reset_steering_filters()
                self.get_logger().info('Tank RIGHT complete — lane acquired (2s cooldown)')
            elif elapsed > self.tank_turn_timeout:
                self._set_tank_steer(False)
                self.state = State.LINE_FOLLOWING
                self.state_entry_time = now
                self.post_turn_until = now + self.post_turn_cooldown
                self.reset_steering_filters()
                self.get_logger().warn('Tank RIGHT timeout — resuming line following (2s cooldown)')

        elif self.state == State.STOPPING:
            self.set_drive_command(twist, 0.0, 0.0)
            if now - self.state_entry_time > self.yellow_stop_duration:
                self.state            = State.LINE_FOLLOWING
                self.state_entry_time = now
                self.reset_steering_filters()
                self.get_logger().info('Stop complete -> resuming LINE_FOLLOWING')

        elif self.state == State.LINE_LOST:
            if green_count >= self.min_follow_area:
                self.state            = State.LINE_FOLLOWING
                self.state_entry_time = now
                self.reset_steering_filters()
                self.get_logger().info(
                    f'Line recovered -> LINE_FOLLOWING | '
                    f'turn_queue={list(self.turn_queue)} ({len(self.turn_queue)} turns)'
                )
            elif now - self.state_entry_time <= self.line_lost_reverse_duration:
                self.set_drive_command(
                    twist,
                    self.line_lost_reverse_speed,
                    max(-1.0, min(1.0, -self.line_lost_angular)),
                )
            else:
                self.set_drive_command(twist, 0.0, 0.0)
                self.get_logger().warn('Line lost after reverse -> full stop', throttle_duration_sec=2.0)

        self.cmd_pub.publish(twist if self.driving_allowed else Twist())
        self.publish_turn_signal()

        self._publish_debug(mask, raw_mask, twist, confidence)

        self.frame_counter += 1
        if self.frame_counter % 30 == 0:
            self.get_logger().info(
                f'[{self.state.value}] steer={twist.angular.z:.3f} '
                f'err={self.error_filtered:.3f} conf={confidence:.2f} '
                f'green={green_count}'
            )

    # ------------------------------------------------------------------
    #  Debug overlay
    # ------------------------------------------------------------------

    def _publish_debug(self, mask, raw_mask, twist, confidence):
        h, w = mask.shape
        dbg = np.zeros((h, w, 3), dtype=np.uint8)
        dbg[mask == 1] = (0, 180, 0)    # green = selected lane
        dbg[mask == 2] = (0, 200, 200)  # cyan  = stop line

        # Cross-lane detection zones
        # Bottom zone (70-95%): primary cross-lane trigger
        bz_y0, bz_y1 = int(h * 0.70), int(h * 0.95)
        bz_col  = (0, 255, 80) if self.cross_armed else (0, 100, 40)
        cv2.rectangle(dbg, (0, bz_y0), (w - 1, bz_y1), bz_col, 1)
        # Mid zone (35-65%): second cross-lane look-ahead (2-lane detection)
        mz_y0, mz_y1 = int(h * 0.35), int(h * 0.65)
        mz_col = (0, 180, 180) if self.cross_count_at_arm == 2 else (0, 60, 80)
        cv2.rectangle(dbg, (0, mz_y0), (w - 1, mz_y1), mz_col, 1)

        # Centre reference
        cv2.line(dbg, (w // 2, 0), (w // 2, h), (50, 50, 50), 1)

        # Centroid dot
        if self.centroid_px is not None:
            cy = int(h * 0.70)
            cv2.circle(dbg, (self.centroid_px, cy), 5, (255, 255, 255), -1)

        # Steering arrow — angular_z > 0 = left, so tip goes left in image
        steer = twist.angular.z
        base  = (w // 2, h - 4)
        tip   = (w // 2 - int(steer * w // 3), h // 4)
        cv2.arrowedLine(dbg, base, tip, (0, 165, 255), 2, tipLength=0.15)

        # Turn queue — show next 3 upcoming turns on the right side
        queue_preview = list(self.turn_queue)[:3] or list(self.route_queue)[:3]
        queue_str = ' > '.join(queue_preview) if queue_preview else 'empty'

        # HUD — left side
        for i, text in enumerate([
            self.state.value,
            f'steer={steer:+.2f}',
            f'err={self.error_filtered:+.2f}',
            f'conf={confidence:.2f}',
            f'xlines={self.last_cross_count} {"ARM" if self.cross_armed else ""}',
        ]):
            cv2.putText(dbg, text, (4, 14 + i * 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1, cv2.LINE_AA)

        # Turn queue — bottom right
        cv2.putText(dbg, f'Q:{queue_str}', (4, h - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 200, 50), 1, cv2.LINE_AA)

        # Pending turn action — top right
        if self.pending_turn_action:
            cv2.putText(dbg, f'>{self.pending_turn_action}', (w - 60, 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (50, 200, 255), 1, cv2.LINE_AA)

        if self.debug_video_writer is not None:
            self.debug_video_writer.write(dbg)

        msg = self.bridge.cv2_to_imgmsg(dbg, encoding='bgr8')
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_frame'
        self.debug_pub.publish(msg)

    # ------------------------------------------------------------------

    def destroy_node(self):
        self._set_tank_steer(False)
        twist = Twist()
        self.cmd_pub.publish(twist)

        turn_msg = String()
        turn_msg.data = "NONE"
        self.turn_signal_pub.publish(turn_msg)

        if self.debug_video_writer is not None:
            self.debug_video_writer.release()

        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = AutonomyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if rclpy.ok():
                node._set_tank_steer(False)
                twist = Twist()
                node.cmd_pub.publish(twist)
        except Exception:
            pass
        node.destroy_node()
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
