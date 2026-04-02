# Obstruction_Handler.py
import math
import json
import subprocess
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
        Initialize with reference to car control functions
        
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
        self.current_obstruction = {
            'x': x,
            'y': y,
            'distance': distance,
            'type': obs_type
        }
        self.state = ObstructionState.DETECTED
        
        print(f"\n[OBSTRUCTION DETECTED] Type: {obs_type} | Pos: ({x}, {y}) | Distance: {distance}mm")
        
        # Step 1: Calculate steering angle to face object
        steering_angle = self.calculate_steering_angle(x, y)
        
        # Step 2: Command car to turn toward object
        self.steer_to_object(steering_angle)
        
        # Step 3: Run CNN classification
        is_real_obstruction = self.classify_with_cnn()
        
        # Step 4: Act based on classification
        if is_real_obstruction:
            self.state = ObstructionState.CONFIRMED
            print("[RESULT] Real obstruction confirmed - executing avoidance")
            self.execute_avoidance()
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
        # Calculate angle from LIDAR position
        angle_rad = math.atan2(y, x)
        angle_deg = math.degrees(angle_rad)
        
        # Convert to steering command (-100 to 100)
        # Normalize angle: -90 (left) to +90 (right)
        steering_angle = max(-100, min(100, angle_deg * (100 / 90)))
        
        return steering_angle
    
    def steer_to_object(self, steering_angle):
        """
        Command car steering to face the detected obstruction.
        
        Args:
            steering_angle: -100 (left) to 100 (right)
        """
        self.state = ObstructionState.STEERING_TO_OBJECT
        print(f"[STEERING] Turning to angle: {steering_angle}°")
        
        # Call car controller steering function
        self.car_controller.set_steering(steering_angle)
        
        # Small delay to allow steering to complete
        import time
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
            # Call the live classification script
            # You can modify this to pass coordinates if needed
            result = subprocess.run(
                ['python3', 'CNN_Model/live_animal_classifier2.py', 
                 '--mode', 'single_inference',
                 '--confidence-threshold', '0.90'],
                cwd='/home/pi/BlackDog_Enforcer',  # Adjust path as needed
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check if animal was detected in output
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
        except:
            pass
        return 0.0
    
    def execute_avoidance(self):
        """
        Execute avoidance maneuver.
        Current implementation: back up and steer away
        """
        import time
        
        print("[DRIVING] Executing avoidance maneuver")
        
        # Back up
        self.car_controller.set_throttle(-30)
        time.sleep(1.0)
        
        # Steer away from object (opposite direction)
        steer_away = -self.current_obstruction.get('steering_angle', 0)
        self.car_controller.set_steering(steer_away)
        time.sleep(0.5)
        
        # Drive forward in new direction
        self.car_controller.set_throttle(25)
        time.sleep(1.5)
        
        # Stop
        self.car_controller.set_throttle(0)
        self.car_controller.set_steering(0)
        
        print("[DRIVING] Avoidance complete - resuming patrol")

    @staticmethod
    def get_status():
        """Return current system status"""
        return {
            'state': ObstructionHandler.state,
            'current_obstruction': ObstructionHandler.current_obstruction
        }
