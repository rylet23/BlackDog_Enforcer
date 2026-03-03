import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)


def trigger_noise():
    while True:
        GPIO.output(17,True)

def stop_noise():
    while True:
        GPIO.output(17,False)

def main():

    target = True

    while True:
        if target == True:
            trigger_noise()
        else:
            stop_noise()
        time.sleep(10)
        target != target

