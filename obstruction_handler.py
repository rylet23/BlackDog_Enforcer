# Obstruction_Handler.py
import math
import re
import json
import subprocess
import time
import sys
from enum import Enum


class ObstructionState(Enum):
    DETECTED = "detected"
    STEERING_TO_OBJECT = "steering_to_object"
    CLASSIFYING = "classifying"
    CONFIRMED = "confirmed"
    BYPASSED = "bypassed"


class ObstructionHandler:
    def __init__(self, car_controller_module):
        """
        Initialize with reference to car control functions.

        Args:
            car_controller_module: Imported Car_Controller module for driving
        """
        self.car_controller = car_controller_module
        self.current_obstruction = None
        self.state = None
        self.last_handled_obstruction = None
        self.last_handle_time = 0
        self.debounce_threshold = 8.0  # seconds - increased to prevent overlap
        self.distance_threshold = 300  # mm - larger threshold for "same object"
        self.is_processing = False  # Flag to indicate we're currently processing an obstruction
        self.camera_working = self.test_camera()

    def test_camera(self):
        """
        Test if the camera is working by trying to capture a frame.
        Returns True if camera is accessible, False otherwise.
        """
        print("[CAMERA TEST] Checking camera availability...")
        try:
            import cv2
            cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
            if not cap.isOpened():
                print("[CAMERA TEST] ERROR: Camera failed to open (cap.isOpened() returned False)")
                return False

            # Try to read a frame
            ret, frame = cap.read()
            cap.release()

            if not ret:
                print("[CAMERA TEST] ERROR: Failed to read frame from camera")
                return False

            print("[CAMERA TEST] SUCCESS: Camera is working and accessible")
            return True

        except ImportError:
            print("[CAMERA TEST] ERROR: OpenCV (cv2) not installed")
            return False
        except Exception as e:
            print(f"[CAMERA TEST] ERROR: {e}")
            return False

    def is_same_obstruction(self, x, y, distance):
        """
        Check if this is the same obstruction we just handled.
        Returns True if we should debounce (skip processing).
        """
        # If we're currently processing an obstruction, skip all new detections
        if self.is_processing:
            return True

        if self.last_handled_obstruction is None:
            return False

        time_since_last = time.time() - self.last_handle_time
        if time_since_last < self.debounce_threshold:
            # Check if position is roughly the same
            dx = x - self.last_handled_obstruction['x']
            dy = y - self.last_handled_obstruction['y']
            distance_moved = math.sqrt(dx ** 2 + dy ** 2)

            # If object hasn't moved much, it's the same obstruction
            if distance_moved < self.distance_threshold:
                return True

        return False

    def handle_obstruction(self, x, y, distance, obs_type):
        """
        Central handler called by Lidar_Monitor when obstruction detected.
        Flow: turn to face object -> classify -> drive toward it

        Args:
            x: X coordinate (mm)
            y: Y coordinate (mm)
            distance: Distance from LIDAR (mm)
            obs_type: "NEW_OBJECT" or "MOVED_OBJECT"
        """
        # Skip if we're already handling the same obstruction
        if self.is_same_obstruction(x, y, distance):
            return

        # Mark that we're starting to process this obstruction
        self.is_processing = True

        try:
            # Step 1: Calculate steering angle to face object
            steering_angle = self.calculate_steering_angle(x, y)

            # Skip objects behind the rover (> +/-90 degrees from forward)
            # These would require reversing which risks hitting walls
            raw_angle = math.degrees(math.atan2(y, x))
            if abs(raw_angle) > 90:
                print(f"[SKIP] Object is behind rover (angle: {raw_angle:.1f} degrees) - ignoring")
                return

            self.current_obstruction = {
                'x': x,
                'y': y,
                'distance': distance,
                'type': obs_type,
                'steering_angle': steering_angle
            }
            self.state = ObstructionState.DETECTED
            print(f"\n[OBSTRUCTION DETECTED] Type: {obs_type} | Pos: ({x}, {y}) | Distance: {distance}mm")

            # Step 2: Turn wheels to face the object
            self.steer_to_object(steering_angle)

            # Step 3: Classify -- wheels stay turned during this
            is_real_obstruction = self.classify_with_cnn()

            # Step 4: Drive toward it if confirmed, otherwise re-center and resume
            if is_real_obstruction:
                self.state = ObstructionState.CONFIRMED
                print("[RESULT] Real obstruction confirmed - executing deterrence")
                self.execute_deterrence(distance)
            else:
                self.state = ObstructionState.BYPASSED
                self.car_controller.set_steering(0)  # Re-center if false positive
                print("[RESULT] False positive - resuming normal operation")

            # Record that we handled this obstruction
            self.last_handled_obstruction = self.current_obstruction
            self.last_handle_time = time.time()

            # Wait a moment to let wheels settle before allowing new detections
            time.sleep(1.0)

        finally:
            # Always mark processing as complete when done
            self.is_processing = False

    def calculate_steering_angle(self, x, y):
        """
        Convert obstruction position to steering angle (-100 to 100).

        Args:
            x: X position (mm, positive = forward)
            y: Y position (mm, positive = left)

        Returns:
            steering_angle: -100 (full left) to 100 (full right)
        """
        angle_rad = math.atan2(y, x)
        angle_deg = math.degrees(angle_rad)

        # Map +/-90 degree forward arc to +/-100 steering range
        # Negate because y positive = left, but we want negative angle for left
        steering_angle = max(-100, min(100, -angle_deg * (100 / 90)))

        return steering_angle

    def steer_to_object(self, steering_angle):
        """
        Turn wheels to face the detected obstruction.
        Zeroes servo first to ensure accurate positioning.

        Args:
            steering_angle: -100 (full left) to 100 (full right)
        """
        self.state = ObstructionState.STEERING_TO_OBJECT
        print(f"[STEERING] Turning to angle: {steering_angle:.1f} degrees")

        # Zero first so new angle is always applied from a known center position
        self.car_controller.set_steering(0)
        time.sleep(0.3)
        self.car_controller.set_steering(steering_angle)
        time.sleep(0.5)

    def classify_with_cnn(self):
        """
        Classify whether the detected object is a real animal obstruction.
        Wheels remain turned toward the object during classification.

        Returns:
            bool: True if real obstruction, False if false positive
        """
        self.state = ObstructionState.CLASSIFYING
        print("[CNN] Initiating classification...")

        # Check if camera is working before attempting classification
        if not self.camera_working:
            print("[CNN] WARNING: Camera test failed at startup - classification may not work")

        try:
            result = subprocess.run(
                ['python3', 'CNN_Model/live_animal_classifier2.py',
                 '--mode', 'single_inference',
                 '--confidence-threshold', '0.90'],
                cwd='/home/blackdog1/BlackDog_Enforcer',
                capture_output=True,
                text=True,
                timeout=3
            )

            is_animal = 'ANIMAL_DETECTED' in result.stdout or result.returncode == 0
            confidence = self.extract_confidence(result.stdout)
            print(f"[CNN] Classification complete - Confidence: {confidence}%")

            return is_animal

        except subprocess.TimeoutExpired:
            print("[CNN] Classification timeout - treating as UNCLEAR (defaulting to false)")
            return False
        except Exception as e:
            print(f"[CNN] Error during classification: {e} - treating as false positive")
            return False

    def extract_confidence(self, cnn_output):
        """Extract confidence score from CNN output"""
        try:
            match = re.search(r'confidence[:\s]*([0-9.]+)', cnn_output, re.IGNORECASE)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return 0.0

    def execute_deterrence(self, distance):
        """
        Drive toward the detected obstruction to deter it.
        Wheels are already facing the object from steer_to_object()
        so just drive forward, then stop and re-center.

        Args:
            distance: Distance to obstruction in mm
        """
        print("[DRIVING] Executing deterrence maneuver")

        # Wheels already turned -- just drive straight toward the object
        # Scale duration to distance: clamp between 0.5s (close) and 3.0s (far)
        drive_duration = max(0.5, min(3.0, distance / 200.0))
        print(f"[DRIVING] Driving toward object for {drive_duration:.1f}s")
        self.car_controller.set_throttle(10)
        time.sleep(drive_duration)

        # Stop and re-center steering
        self.car_controller.set_throttle(0)
        self.car_controller.set_steering(0)

        print("[DRIVING] Deterrence complete - resuming patrol")

    def get_status(self):
        return {
            'state': self.state,
            'current_obstruction': self.current_obstruction,
            'camera_working': self.camera_working
        }