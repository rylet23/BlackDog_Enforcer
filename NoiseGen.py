import RPi.GPIO as GPIO

class NoiseManager:
    def __init__(self, pin=6):
        """Initializes the GPIO settings for the noise component."""
        self.pin = pin
        
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        
        GPIO.output(self.pin, GPIO.LOW)

    def set_state(self, mode):
        """
        Main control function:
        Pass 1 for NoiseOn
        Pass 0 for NoiseOff
        """
        if mode == 1:
            GPIO.output(self.pin, GPIO.HIGH)
            print(f"Noise toggled: ON (Pin {self.pin})")
        elif mode == 0:
            GPIO.output(self.pin, GPIO.LOW)
            print(f"Noise toggled: OFF (Pin {self.pin})")
        else:
            print(f"Invalid input '{mode}'. Please use 1 (On) or 0 (Off).")

    def cleanup(self):
        """Resets the GPIO pins to a safe state."""
        GPIO.output(self.pin, GPIO.LOW)
        GPIO.cleanup(self.pin)