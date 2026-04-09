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

def set_throttle(percent):
    percent = max(-100, min(100, percent))
    if percent == 0:
        esc.ChangeDutyCycle(0)  # completely stop signal = true neutral
    else:
        duty = 7.5 + (percent / 200) * 5
        esc.ChangeDutyCycle(duty)

def set_steering(angle):
    """-100..100 => full left..full right"""
    angle = max(-100, min(100, angle))
    duty = 7.5 + (angle / 200) * 5
    steer.ChangeDutyCycle(duty)

def drive_forward(throttle_percent=25, duration=2.0):
    """Drive forward for specified duration"""
    set_throttle(throttle_percent)
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