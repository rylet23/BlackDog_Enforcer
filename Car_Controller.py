import RPi.GPIO as GPIO
import time

# --- Pin setup ---
ESC_PIN = 17
STEER_PIN = 18
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(ESC_PIN, GPIO.OUT)
GPIO.setup(STEER_PIN, GPIO.OUT)

# --- PWM setup (50Hz for both) ---
esc = GPIO.PWM(ESC_PIN, 50)
steer = GPIO.PWM(STEER_PIN, 50)
esc.start(0)
steer.start(0)

DRIVE_DURATION = 2.0  # seconds
STEERING_TRIM = 0.0  # Tweak this! E.g., +0.2 if it drifts right, -0.2 if it drifts left

    # Global to track last steering direction
last_steering_angle = 0

#def set_throttle(percent):
 #   percent = max(-100, min(100, percent))
  #  if percent == 0:
   #     esc.ChangeDutyCycle(0)
    #else:
     #   duty = 7.5 + (percent / 200) * 5  
      #  esc.ChangeDutyCycle(duty)
def set_throttle(percent):
    percent = max(-100, min(100, percent))
    # Remove the 'if percent == 0' block entirely
    duty = 7.5 + (percent / 200) * 5 
    esc.ChangeDutyCycle(duty)

def set_steering(angle):
    global last_steering_angle
    angle = max(-100, min(100, angle))

    # Apply trim to the physical center (7.5)
    true_center = 7.5 + STEERING_TRIM

    if angle == 0:
        # Smoothly return to center without oscillation
        steer.ChangeDutyCycle(true_center)
        last_steering_angle = 0
    else:
        # Include trim in the angle calculation
        duty = true_center + (angle / 200) * 5
        steer.ChangeDutyCycle(duty)
        last_steering_angle = angle

def drive_forward(throttle_percent=10, duration=2.0):
    """Drive forward for specified duration"""
    set_throttle(throttle_percent)
    #set_throttle(80)
    time.sleep(duration)
    set_throttle(0)

def turn_to_angle(steering_angle, duration=0.5):
    """Turn to specific angle"""
    set_steering(steering_angle)
    time.sleep(duration)
    set_steering(0)

def stop_all():
    """Emergency stop"""
    set_throttle(0)
    set_steering(0)

def arm_esc():
    """Arm the ESC - call this once before using throttle"""
    print("Arming ESC...")
    set_throttle(0)
    set_steering(0)
    time.sleep(3)
    print("ESC armed.")

def cleanup():
    """Cleanly shut down PWM and GPIO - call only when fully done"""
    esc.stop()
    steer.stop()
    GPIO.cleanup()


# --- Only runs when executed directly, NOT when imported ---
# This prevents GPIO.cleanup() from destroying PWM channels
# when Car_Controller is imported by obstruction_handler or other modules
if __name__ == "__main__":
    try:
        arm_esc()
        print("Car_Controller ready.")
    finally:
        cleanup()
