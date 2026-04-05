import RPi.GPIO as GPIO #throws an error if not on a Raspberry pi
import time

# --- Pin setup ---
ESC_PIN = 17      # throttle
STEER_PIN = 23    # steering servo
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(ESC_PIN, GPIO.OUT)
GPIO.setup(STEER_PIN, GPIO.OUT)

# --- PWM setup (50Hz for both) ---
esc = GPIO.PWM(ESC_PIN, 50)
steer = GPIO.PWM(STEER_PIN, 50)
esc.start(0)
steer.start(0)

def set_throttle(percent):
    """-100..100 => reverse..forward"""
    percent = max(-100, min(100, percent))
    duty = 7.5 + (percent / 200) * 5  # 5?10%
    esc.ChangeDutyCycle(duty)

def set_steering(angle):
    """-100..100 => full left..full right"""
    angle = max(-100, min(100, angle))
    duty = 7.5 + (angle / 200) * 5  # 5?10%
    steer.ChangeDutyCycle(duty)

try:
    print("Arming ESC...")
    set_throttle(0)
    time.sleep(3)

    print("Centering steering...")
    set_steering(0)
    time.sleep(1)

    print("Forward 25%, turn right")
    set_throttle(25)
    set_steering(50)
    time.sleep(2)

    print("Straight ahead")
    set_steering(0)
    time.sleep(1)

    print("Turn left")
    set_steering(-50)
    time.sleep(2)

    print("Stop")
    set_throttle(0)
    set_steering(0)
    time.sleep(1)

finally:
    print("Cleaning up GPIO...")
    esc.stop()
    steer.stop()
    GPIO.cleanup()
