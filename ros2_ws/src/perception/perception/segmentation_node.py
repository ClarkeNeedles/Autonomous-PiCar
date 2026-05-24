#!/usr/bin/env python3

import fcntl
import os
import time
import subprocess
from datetime import datetime
import numpy as np
import cv2

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32, Int32
from cv_bridge import CvBridge

from tflite_runtime.interpreter import Interpreter, load_delegate


class SegmentationNode(Node):
    def __init__(self):
        super().__init__('segmentation_node')

        self.declare_parameter('model_path', '/home/robocar/elec-392-project-blekinge-12/segmentation_v5.tflite')
        self.declare_parameter('camera_width', 640)
        self.declare_parameter('camera_height', 480)
        self.declare_parameter('camera_fps', 15)
        self.declare_parameter('mask_topic', '/segmentation/mask')
        self.declare_parameter('fps_topic', '/segmentation/fps')
        self.declare_parameter('green_pixels_topic', '/segmentation/green_pixels')
        self.declare_parameter('green_class_id', 1)
        self.declare_parameter('debug_log_every_n_frames', 30)
        self.declare_parameter('record_raw_video', False)
        self.declare_parameter('record_debug_video', False)
        self.declare_parameter('video_output_dir', os.path.expanduser('~/recordings'))

        model_path = self.get_parameter('model_path').value
        self.camera_width = int(self.get_parameter('camera_width').value)
        self.camera_height = int(self.get_parameter('camera_height').value)
        self.camera_fps = int(self.get_parameter('camera_fps').value)
        mask_topic = self.get_parameter('mask_topic').value
        fps_topic = self.get_parameter('fps_topic').value
        green_pixels_topic = self.get_parameter('green_pixels_topic').value
        self.green_class_id = int(self.get_parameter('green_class_id').value)
        self.debug_log_every_n_frames = int(self.get_parameter('debug_log_every_n_frames').value)
        self.record_raw_video = bool(self.get_parameter('record_raw_video').value)
        self.record_debug_video = bool(self.get_parameter('record_debug_video').value)
        self.video_output_dir = str(self.get_parameter('video_output_dir').value)

        self.video_writer = None
        self.debug_video_writer = None
        if self.record_raw_video or self.record_debug_video:
            os.makedirs(self.video_output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        if self.record_raw_video:
            video_path = os.path.join(self.video_output_dir, f'run_{timestamp}.mp4')
            self.video_writer = cv2.VideoWriter(
                video_path, fourcc, self.camera_fps,
                (self.camera_width, self.camera_height)
            )
            self.get_logger().info(f'Recording raw video to {video_path}')
        if self.record_debug_video:
            debug_path = os.path.join(self.video_output_dir, f'debug_{timestamp}.mp4')
            self.debug_video_writer = cv2.VideoWriter(
                debug_path, fourcc, self.camera_fps,
                (self.camera_width * 2, self.camera_height)
            )
            self.get_logger().info(f'Recording debug video to {debug_path}')

        self.bridge = CvBridge()
        self.proc = None
        self.buffer = b''

        self.frame_counter = 0
        self.last_publish_time = None
        self.last_log_time = time.perf_counter()
        self.last_green_detected = None

        self.get_logger().info(f'Loading EdgeTPU model: {model_path}')
        self.interpreter = Interpreter(
            model_path=model_path,
            experimental_delegates=[load_delegate('libedgetpu.so.1')]
        )
        self.interpreter.allocate_tensors()

        input_details = self.interpreter.get_input_details()[0]
        self.model_h = int(input_details['shape'][1])
        self.model_w = int(input_details['shape'][2])
        self.input_index = input_details['index']
        self.output_index = self.interpreter.get_output_details()[0]['index']

        self.get_logger().info(
            f'Model input: {self.model_w}x{self.model_h}, '
            f'output shape: {self.interpreter.get_output_details()[0]["shape"]}'
        )

        self.mask_pub = self.create_publisher(Image, mask_topic, 10)
        self.fps_pub = self.create_publisher(Float32, fps_topic, 10)
        self.green_pixels_pub = self.create_publisher(Int32, green_pixels_topic, 10)

        self._start_camera()

        timer_period = 1.0 / float(self.camera_fps)
        self.timer = self.create_timer(timer_period, self._on_timer)

        self.get_logger().info(
            f'SegmentationNode opened camera at {self.camera_width}x{self.camera_height} @ {self.camera_fps} FPS'
        )
        self.get_logger().info(f'Publishing mask on {mask_topic}')
        self.get_logger().info(f'Publishing measured segmentation FPS on {fps_topic}')
        self.get_logger().info(f'Publishing green pixel count on {green_pixels_topic}')
        self.get_logger().info(f'Using green_class_id={self.green_class_id}')

    def _start_camera(self):
        cmd = [
            'rpicam-vid',
            '-t', '0',
            '--codec', 'mjpeg',
            '--width', str(self.camera_width),
            '--height', str(self.camera_height),
            '--framerate', str(self.camera_fps),
            '--nopreview',
            '-o', '-',
        ]

        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0
        )
        # Non-blocking so _read_latest_frame can drain the full pipe each tick
        fd = self.proc.stdout.fileno()
        fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)

    def _read_latest_frame(self):
        if self.proc is None or self.proc.stdout is None:
            return None

        # Drain every byte the pipe has right now (non-blocking)
        try:
            while True:
                chunk = self.proc.stdout.read(65536)
                if not chunk:
                    break
                self.buffer += chunk
        except BlockingIOError:
            pass

        if not self.buffer:
            return None

        # Walk all complete JPEGs; keep only the last valid frame
        latest_frame = None
        pos = 0
        consumed_up_to = 0

        while True:
            start = self.buffer.find(b'\xff\xd8', pos)
            if start == -1:
                break
            end = self.buffer.find(b'\xff\xd9', start + 2)
            if end == -1:
                break
            end += 2  # include the end marker

            frame = cv2.imdecode(
                np.frombuffer(self.buffer[start:end], dtype=np.uint8),
                cv2.IMREAD_COLOR
            )
            if frame is not None:
                latest_frame = frame
            consumed_up_to = end
            pos = end

        # Discard processed data; keep any incomplete trailing bytes
        if consumed_up_to > 0:
            self.buffer = self.buffer[consumed_up_to:]

        return latest_frame

    def _on_timer(self):
        if not rclpy.ok():
            return
        loop_start = time.perf_counter()

        frame = self._read_latest_frame()
        if frame is None:
            self.get_logger().warn('No frame received', throttle_duration_sec=2.0)
            return

        if self.video_writer is not None:
            self.video_writer.write(frame)

        self.video_writer_frame = frame.copy()

        if frame.shape[1] != self.model_w or frame.shape[0] != self.model_h:
            frame = cv2.resize(frame, (self.model_w, self.model_h), interpolation=cv2.INTER_LINEAR)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.interpreter.tensor(self.input_index)()[0][:] = rgb_frame

        self.interpreter.invoke()

        output = self.interpreter.get_tensor(self.output_index)
        if output.ndim == 4:
            mask = np.argmax(output[0], axis=-1).astype(np.uint8)
        else:
            mask = output[0].astype(np.uint8)

        if self.debug_video_writer is not None:
            color_mask = np.zeros((self.model_h, self.model_w, 3), dtype=np.uint8)
            color_mask[mask == 1] = (0, 255, 0)    # green = road
            color_mask[mask == 2] = (0, 255, 255)   # yellow = stop line
            mask_resized = cv2.resize(
                color_mask, (self.camera_width, self.camera_height),
                interpolation=cv2.INTER_NEAREST
            )
            raw_resized = cv2.resize(
                self.video_writer_frame, (self.camera_width, self.camera_height),
                interpolation=cv2.INTER_LINEAR
            )
            side_by_side = np.hstack([raw_resized, mask_resized])
            self.debug_video_writer.write(side_by_side)

        green_pixels = int(np.count_nonzero(mask == self.green_class_id))
        green_detected = green_pixels > 0
        self.frame_counter += 1


        green_msg = Int32()
        green_msg.data = green_pixels
        self.green_pixels_pub.publish(green_msg)

        if self.last_green_detected is None or green_detected != self.last_green_detected:
            if green_detected:
                self.get_logger().info(
                    f'GREEN DETECTED: {green_pixels} pixels of class {self.green_class_id}'
                )
            else:
                self.get_logger().info(
                    f'NO GREEN DETECTED for class {self.green_class_id}'
                )
            self.last_green_detected = green_detected
        elif self.debug_log_every_n_frames > 0 and self.frame_counter % self.debug_log_every_n_frames == 0:
            self.get_logger().info(
                f'Green debug: pixels={green_pixels}, detected={green_detected}, class={self.green_class_id}'
            )

        mask_msg = self.bridge.cv2_to_imgmsg(mask, encoding='mono8')
        mask_msg.header.stamp = self.get_clock().now().to_msg()
        mask_msg.header.frame_id = 'camera_frame'
        self.mask_pub.publish(mask_msg)

        now = time.perf_counter()
        if self.last_publish_time is not None:
            dt = now - self.last_publish_time
            if dt > 0.0:
                measured_fps = 1.0 / dt

                fps_msg = Float32()
                fps_msg.data = float(measured_fps)
                self.fps_pub.publish(fps_msg)

                if now - self.last_log_time >= 1.0:
                    loop_ms = (now - loop_start) * 1000.0
                    self.get_logger().info(
                        f'Real segmentation FPS: {measured_fps:.2f} | green_pixels: {green_pixels} | loop time: {loop_ms:.1f} ms'
                    )
                    self.last_log_time = now

        self.last_publish_time = now

    def destroy_node(self):
        if self.video_writer is not None:
            self.video_writer.release()
            self.get_logger().info('Video saved.')
        if self.debug_video_writer is not None:
            self.debug_video_writer.release()
            self.get_logger().info('Debug video saved.')
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SegmentationNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
