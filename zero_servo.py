import RPi.GPIO as GPIO
import time

# --- Pin setup ---
STEER_PIN = 18
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(STEER_PIN, GPIO.OUT)

# --- PWM setup (50Hz) ---
steer = GPIO.PWM(STEER_PIN, 50)
steer.start(7.5)
time.sleep(0.5)

def set_steering(angle):
    """Set steering angle (-100 to 100)"""
    #angle = max(-100, min(100, angle))
    duty = 7.5 + (angle / 200) * 5
    steer.ChangeDutyCycle(duty)

try:
    target = 0
    set_steering(target)
    print("holding fr 3 sec")
    for i in range(5, 0, -1):
        print(f"{i}..")
        time.sleep(1)
#    test_angle = 50
 #   print(f"Moving to {test_angle}...")
    #set_steering(test_angle)
    time.sleep(1)
    
finally:
    #set_steering(0)
    #time.sleep(0.5)
    print("Cleaning up GPIO...")
    steer.stop()
    GPIO.cleanup()
    print("Done!")
