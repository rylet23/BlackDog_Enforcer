import RPi.GPIO as GPIO
import time

# --- Pin setup ---
STEER_PIN = 18
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(STEER_PIN, GPIO.OUT)

# --- PWM setup (50Hz) ---
steer = GPIO.PWM(STEER_PIN, 50)
steer.start(0)

def set_steering(angle):
    """Set steering angle (-100 to 100)"""
    angle = max(-100, min(100, angle))
    duty = 7.5 + (angle / 200) * 5
    steer.ChangeDutyCycle(duty)

try:
    print("Centering steering servo to dead center (0°)...")
    set_steering(0)
    time.sleep(2)
    
finally:
    print("Cleaning up GPIO...")
    steer.stop()
    GPIO.cleanup()
    print("Done!")
