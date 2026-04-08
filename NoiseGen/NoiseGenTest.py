import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(6, GPIO.OUT)
while True:
    GPIO.output(6, True)
    time.sleep(10)
    GPIO.output(6, False)
    time.sleep(10) 
