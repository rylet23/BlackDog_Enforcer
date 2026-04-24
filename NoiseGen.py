import RPi.GPIO as GPIO
import time
class NoiseManager:
    def __init__(self, pin=27):
        self.pin = pin
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)

    def set_state(self, mode, duration=1):
        """
        Modified to auto-off if mode is 1.
        If you call set_state(1), it will run for 'duration' then stop.
        """
        if mode == 1:
            GPIO.output(self.pin, GPIO.HIGH)
            print(f"Noise toggled: ON (GPIO {self.pin})")
            
            # This is the "Auto-Off" logic inside the call
            time.sleep(duration)
            
            GPIO.output(self.pin, GPIO.LOW)
            print(f"Noise toggled: OFF (GPIO {self.pin})")
            
        elif mode == 0:
            GPIO.output(self.pin, GPIO.LOW)
            print(f"Noise toggled: OFF (GPIO {self.pin})")

    def cleanup(self):
        GPIO.output(self.pin, GPIO.LOW)
        GPIO.cleanup(self.pin)
