import RPi.GPIO as GPIO
import time

# --- Pin setup ---
ESC_PIN = 18
STEER_PIN = 17
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

def set_throttle(percent):
    """-100..100 => reverse..forward"""
    percent = max(-100, min(100, percent))
    duty = 7.5 + (percent / 200) * 5
    esc.ChangeDutyCycle(duty)

def set_steering(angle):
    """-100..100 => full left..full right"""
    angle = max(-100, min(100, angle))
    duty = 7.5 + (angle / 200) * 5
    steer.ChangeDutyCycle(duty)

# Add these functions to be callable from other modules
def drive_forward(throttle_percent=25, duration=2.0):
    """Drive forward for specified duration"""
    import time
    set_throttle(throttle_percent)
    time.sleep(duration)
    set_throttle(0)

def turn_to_angle(steering_angle, duration=0.5):
    """Turn to specific angle"""
    import time
    set_steering(steering_angle)
    time.sleep(duration)
    set_steering(0)

def stop_all():
    """Emergency stop"""
    set_throttle(0)
    set_steering(0)

try:
    print("Arming ESC...")
    set_throttle(0)
    set_steering(0)
    time.sleep(3)
    print("ESC armed. Driving forward...")

    set_throttle(25)
    set_steering(0)
    time.sleep(DRIVE_DURATION)

    set_throttle(0)
    print("Drive complete. Stopped.")

finally:
    esc.stop()
    steer.stop()
    GPIO.cleanup()

