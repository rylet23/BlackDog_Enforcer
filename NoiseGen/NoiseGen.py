import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(6, GPIO.OUT)

def NoiseOn(target):
    while True:
        GPIO.output(6, True)

def NoiseOff(target):
    while True:
	    GPIO.output(6, False)
