import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)

def NoiseOn(target == True):
    while True:
        GPIO.output(17, True)

def NoiseOff(target == False):
    while True:
	GPIO.output(17, False)
