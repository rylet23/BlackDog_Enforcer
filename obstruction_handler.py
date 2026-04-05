# Obstruction_Handler.py
import math
import re  # FIX: was missing, needed by extract_confidence()
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

    def handle_obstruction(self, x, y, distance, obs_type):
        """
        Central handler called by Lidar_Monitor when obstruction detected.

        Args:
            x: X coordinate (mm)
            y: Y coordinate (mm)
            distance: Distance from LIDAR (mm)
            obs_type: "NEW_OBJECT" or "MOVED_OBJECT"
        """
        # Step 1: Calculate steering angle to face object
        steering_angle = self.calculate_steering_angle(x, y)

        # Skip objects behind the rover (angle clamped to ±100 means > ±90° from forward)
        # These would require reversing which risks hitting walls
        raw_angle = math.degrees(math.atan2(y, x))
        if abs(raw_angle) > 90:
            print(f"[SKIP] Object is behind rover (angle: {raw_angle:.1f}°) - ignoring")
            return

        self.current_obstruction = {
            'x': x,
            'y': y,
            'distance': distance,
            'type': obs_type,
            'steering_angle': steering_angle  # FIX: store so execute_avoidance() can use it
        }
        self.state = ObstructionState.DETECTED

        print(f"\n[OBSTRUCTION DETECTED] Type: {obs_type} | Pos: ({x}, {y}) | Distance: {distance}mm")

        # Step 2: Command car to turn toward object
        self.steer_to_object(steering_angle)

        # Step 3: Run CNN classification
        is_real_obstruction = self.classify_with_cnn()

        # Step 4: Act based on classification
        if is_real_obstruction:
            self.state = ObstructionState.CONFIRMED
            print("[RESULT] Real obstruction confirmed - executing deterrence")
            self.execute_deterrence(distance)
        else:
            self.state = ObstructionState.BYPASSED
            print("[RESULT] False positive - resuming normal operation")

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

        # Normalize: atan2 returns -180..180, map to -100..100
        steering_angle = max(-100, min(100, angle_deg * (100 / 90)))

        return steering_angle

    def steer_to_object(self, steering_angle):
        """
        Command car steering to face the detected obstruction.
        Zeroes the servo first to ensure accurate positioning.

        Args:
            steering_angle: -100 (left) to 100 (right)
        """
        self.state = ObstructionState.STEERING_TO_OBJECT
        print(f"[STEERING] Turning to angle: {steering_angle}°")

        # Zero servo first so the new angle is applied from a known position
        self.car_controller.set_steering(0)
        time.sleep(0.3)
        self.car_controller.set_steering(steering_angle)
        time.sleep(0.5)

    def classify_with_cnn(self):
        """
        Trigger CNN model to classify if object is real obstruction.

        Returns:
            bool: True if obstruction confirmed, False if false positive
        """
        self.state = ObstructionState.CLASSIFYING
        print("[CNN] Initiating classification...")

        try:
            result = subprocess.run(
                ['python3', 'CNN_Model/live_animal_classifier2.py',
                 '--mode', 'single_inference',
                 '--confidence-threshold', '0.90'],
                cwd='/home/blackdog1/BlackDog_Enforcer',
                capture_output=True,
                text=True,
                timeout=5
            )

            is_animal = 'ANIMAL_DETECTED' in result.stdout or result.returncode == 0

            confidence = self.extract_confidence(result.stdout)
            print(f"[CNN] Classification complete - Confidence: {confidence}%")

            return is_animal

        except subprocess.TimeoutExpired:
            print("[CNN] Classification timeout - treating as real threat")
            return True
        except Exception as e:
            print(f"[CNN] Error during classification: {e} - treating as real threat")
            return True

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
        Steers to face the object, drives forward proportional
        to distance, then stops and re-centers.

        Args:
            distance: Distance to obstruction in mm
        """
        print("[DRIVING] Executing deterrence maneuver")

        steering_angle = self.current_obstruction.get('steering_angle', 0)

        # Steer to face the object
        self.car_controller.set_steering(steering_angle)
        time.sleep(0.3)

        # Drive forward — scale duration to distance so it doesn't overshoot
        # Clamp between 0.5s (close) and 3.0s (far) based on distance in mm
        drive_duration = max(0.5, min(3.0, distance / 1000.0))
        print(f"[DRIVING] Driving toward object for {drive_duration:.1f}s")
        self.car_controller.set_throttle(30)
        time.sleep(drive_duration)

        # Stop and re-center steering
        self.car_controller.set_throttle(0)
        self.car_controller.set_steering(0)

        print("[DRIVING] Deterrence complete - resuming patrol")

    def get_status(self):
        # FIX: was @staticmethod referencing instance variables - converted to instance method
        return {
            'state': self.state,
            'current_obstruction': self.current_obstruction
        }