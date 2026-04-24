import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.OUT)
while True:
    GPIO.output(27, False)
    time.sleep(10)
    GPIO.output(27, False)
    time.sleep(10) 
    
