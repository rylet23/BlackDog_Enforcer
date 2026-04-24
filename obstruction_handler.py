# Obstruction_Handler.py
import math
import re
import json
import subprocess
import time
import sys
import os
from enum import Enum
#import NoiseGen
#noise_controller = NoiseGen.NoiseManager(pin=27)

class ObstructionState(Enum):
    DETECTED = "detected"
    STEERING_TO_OBJECT = "steering_to_object"
    CLASSIFYING = "classifying"
    CONFIRMED = "confirmed"
    BYPASSED = "bypassed"


class ObstructionHandler:
    def __init__(self, car_controller_module):
        self.car_controller = car_controller_module
        self.current_obstruction = None
        self.state = None
        self.last_handled_obstruction = None
        self.last_handle_time = 0
        self.debounce_threshold = 10.0
        self.distance_threshold = 200
        self.is_processing = False
        self.camera_working = self.test_camera()
        self.car_controller.arm_esc()

        # Resolve CNN script and model paths once at startup so we can verify they exist
        self.script_dir = '/home/blackdog1/BlackDog_Enforcer'
        self.cnn_script = os.path.join(self.script_dir, 'CNN_Model', 'live_animal_classifier2.py')
        self.model_path = os.path.join(self.script_dir, 'animal_classifier.pth')
        self._verify_cnn_paths()

    def _verify_cnn_paths(self):
        print("[CNN INIT] Verifying CNN paths...")
        if os.path.exists(self.cnn_script):
            print(f"[CNN INIT] ✓ Script found: {self.cnn_script}")
        else:
            print(f"[CNN INIT] ✗ Script NOT found: {self.cnn_script}")
        if os.path.exists(self.model_path):
            print(f"[CNN INIT] ✓ Model found: {self.model_path}")
        else:
            print(f"[CNN INIT] ✗ Model NOT found: {self.model_path}")

    def test_camera(self):
        print("[CAMERA TEST] Checking camera availability...")
        try:
            import cv2
            cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
            if not cap.isOpened():
                print("[CAMERA TEST] ERROR: Camera failed to open")
                return False
            ret, frame = cap.read()
            cap.release()
            if not ret:
                print("[CAMERA TEST] ERROR: Failed to read frame")
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
        if self.is_processing:
            return True
        if (time.time() - self.last_handle_time) < self.debounce_threshold:
            return True
        return False

    def handle_obstruction(self, x, y, distance, obs_type):
        if self.is_same_obstruction(x, y, distance):
            return

        self.is_processing = True
        try:
            steering_angle = self.calculate_steering_angle(x, y)
            raw_angle = math.degrees(math.atan2(y, x))

            self.current_obstruction = {
                'x': x, 'y': y, 'distance': distance,
                'type': obs_type, 'steering_angle': steering_angle
            }
            self.state = ObstructionState.DETECTED
            print(f"\n[OBSTRUCTION DETECTED] Type: {obs_type} | Pos: ({x}, {y}) | Distance: {distance}mm")

            self.steer_to_object(steering_angle)
            is_real_obstruction = self.classify_with_cnn()

            if is_real_obstruction:
                self.state = ObstructionState.CONFIRMED
                print("[RESULT] Real obstruction confirmed - executing deterrence")
 #               noise_controller.set_state(1, duration=10)
                self.execute_deterrence(distance)
            else:
                self.state = ObstructionState.BYPASSED
                self.car_controller.set_steering(0)
                print("[RESULT] False positive - resuming normal operation")

            self.last_handled_obstruction = self.current_obstruction
            self.last_handle_time = time.time()
            time.sleep(1.0)

        finally:
            self.is_processing = False

    def calculate_steering_angle(self, x, y):
        L = 250.0
        if y == 0:
            return 0.0
        R = (x ** 2 + y ** 2) / (2 * y)
        steering_angle_rad = math.atan(L / R)
        steering_angle_deg = math.degrees(steering_angle_rad)
        MAX_WHEEL_ANGLE = 30.0
        pwm_val = (steering_angle_deg / MAX_WHEEL_ANGLE) * 100
        return max(-100, min(100, -pwm_val))

    def steer_to_object(self, steering_angle):
        self.state = ObstructionState.STEERING_TO_OBJECT
        print(f"[STEERING] Turning to angle: {steering_angle:.1f} degrees")
        self.car_controller.set_throttle(0)
        self.car_controller.set_steering(steering_angle)
        time.sleep(0.5)

    def classify_with_cnn(self):
        self.state = ObstructionState.CLASSIFYING
        print("[CNN] Initiating classification...")

        if not self.camera_working:
            print("[CNN] WARNING: Camera unavailable - treating as false positive")
            return False

        if not os.path.exists(self.cnn_script):
            print(f"[CNN] ERROR: Script not found at {self.cnn_script} - treating as false positive")
            return False

        if not os.path.exists(self.model_path):
            print(f"[CNN] ERROR: Model not found at {self.model_path} - treating as false positive")
            return False

        try:
            result = subprocess.run(
                [
                    'python3', self.cnn_script,
                    '--mode', 'single_inference',
                    '--confidence-threshold', '0.50',
                    '--model', self.model_path
                ],
                cwd=self.script_dir,
                capture_output=True,
                text=True,
                timeout=30  # increased to allow for 5 frames
            )

            # Always print stderr so errors are visible in the terminal
            if result.stderr.strip():
                for line in result.stderr.strip().splitlines():
                    print(f"[CNN stderr] {line}")

            # Print raw stdout for debugging
            if result.stdout.strip():
                print(f"[CNN stdout] {result.stdout.strip()}")
            else:
                print(f"[CNN] WARNING: No stdout output (returncode={result.returncode})")

            is_animal = 'ANIMAL_DETECTED' in result.stdout
            confidence = self.extract_confidence(result.stdout)
            print(f"[CNN] Classification complete - Animal: {is_animal} | Confidence: {confidence:.1f}%")
            return is_animal

        except subprocess.TimeoutExpired:
            print("[CNN] Timeout - treating as false positive")
            return False
        except Exception as e:
            print(f"[CNN] Error: {e} - treating as false positive")
            return False

    def extract_confidence(self, cnn_output):
        try:
            match = re.search(r'confidence[:\s]*([0-9.]+)', cnn_output, re.IGNORECASE)
            if match:
                return float(match.group(1)) * 100  # convert 0.97 → 97.0%
        except Exception:
            pass
        return 0.0

  #  def execute_deterrence(self, distance):
 #       print("[DRIVING] Executing deterrence maneuver")
#
  #      TURN_DURATION   = 0.5
 #       SETTLE_DURATION = 0.3
#
  #      total_duration    = max(0.5, min(3.0, distance / 1000.0))
 #       straight_duration = max(0.0, total_duration - TURN_DURATION)
#
   #     print(f"[DRIVING] Phase 1 - Driving turned for {TURN_DURATION:.1f}s")
  #      self.car_controller.set_throttle(10)
 #       time.sleep(TURN_DURATION)
#
    #    print(f"[DRIVING] Phase 2 - Stopped, recentering wheels ({SETTLE_DURATION:.1f}s)")
   #     self.car_controller.set_throttle(0)
  #      self.car_controller.set_steering(0)
 #       time.sleep(SETTLE_DURATION)
#
    #    if straight_duration > 0:
   #         print(f"[DRIVING] Phase 3 - Driving straight for {straight_duration:.1f}s")
  #          self.car_controller.set_throttle(10)
 #           time.sleep(straight_duration)
#
  #      self.car_controller.set_throttle(0)
 #       self.car_controller.set_steering(0)
#        print("[DRIVING] Deterrence complete - resuming patrol")

    def execute_deterrence(self, distance):
        print("[DRIVING] Executing deterrence maneuver")

        # Increased to 20% - just enough to move smoothly
        DRIVE_THROTTLE = 20  
        
        # Calculate durations
        total_duration = max(1.0, min(3.0, distance / 800.0))
        turn_phase = 0.7 
        straight_phase = total_duration - turn_phase

        # Phase 1: The Move
        print(f"[DRIVING] Phase 1 - Initial Charge ({turn_phase:.1f}s)")
        self.car_controller.set_throttle(DRIVE_THROTTLE)
        time.sleep(turn_phase)

        # Phase 2: The Glide (NO STOPPING)
        print("[DRIVING] Phase 2 - Straightening wheels while rolling")
        self.car_controller.set_steering(0)
        # We stay at DRIVE_THROTTLE here so there is no jerk!
        time.sleep(0.4) 

        # Phase 3: The Follow-through
        if straight_phase > 0:
            print(f"[DRIVING] Phase 3 - Straight finish ({straight_phase:.1f}s)")
            self.car_controller.set_throttle(DRIVE_THROTTLE)
            time.sleep(straight_phase)

        # Final Stop
        self.car_controller.set_throttle(0)
        self.car_controller.set_steering(0)
        print("[DRIVING] Deterrence complete")
#    def execute_deterrence(self, distance):
 #       print("[DRIVING] Executing deterrence maneuver")

        # --- TUNING CONSTANTS ---
        # Bump throttle to 40% to ensure it actually moves the car's weight
  #      DET_THROTTLE = 22
   #     TURN_DURATION = 0.5  # Increased from 0.5 to get moving
        
        # Calculate straight duration based on distance (min 1s, max 3s)
    #    total_duration = max(1.5, min(4.0, distance / 500.0))
     #   straight_duration = max(1.0, total_duration - TURN_DURATION)

        # Phase 1: The Initial Turn & Charge
      #  print(f"[DRIVING] Phase 1 - Charging at Angle ({TURN_DURATION:.1f}s)")
       # self.car_controller.set_throttle(DET_THROTTLE)
        #time.sleep(TURN_DURATION)

        # Phase 2: Straighten out WITHOUT stopping
        #print(f"[DRIVING] Phase 2 - Straightening wheels while moving")
        # Notice: We do NOT set throttle to 0 here. We keep the momentum!
        #self.car_controller.set_steering(0)
        #time.sleep(0.4) # Brief pause just for the servo to physically move

        # Phase 3: The Final Push
        #if straight_duration > 0:
         #   print(f"[DRIVING] Phase 3 - Full speed straight ({straight_duration:.1f}s)")
          #  self.car_controller.set_throttle(DET_THROTTLE + 5) # Extra kick for the finish
           # time.sleep(straight_duration)

        # Final Stop
        #self.car_controller.set_throttle(0)
        #self.car_controller.set_steering(0)
        #print("[DRIVING] Deterrence complete - resuming patrol")
    def get_status(self):
        return {
            'state': self.state,
            'current_obstruction': self.current_obstruction,
            'camera_working': self.camera_working
        }
