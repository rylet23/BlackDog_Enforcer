import sys
import json
import time
import RPi.GPIO as GPIO #throws an error if not on a Raspberry pi

# --- Pin setup ---
ESC_PIN = 18      # throttle
STEER_PIN = 17    # steering servo
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(ESC_PIN, GPIO.OUT)
GPIO.setup(STEER_PIN, GPIO.OUT)

# --- PWM setup (50Hz for both) ---
esc = GPIO.PWM(ESC_PIN, 50)
steer = GPIO.PWM(STEER_PIN, 50)
esc.start(0)
steer.start(0)

# Configuration
CONFIDENCE_THRESHOLD = 0.90
DRIVE_DURATION = 2.0  # seconds

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

def drive_forward(duration):
    """
    Drive the car forward for specified duration
    """
    #Wheels Forward, Motor Off
    set_throttle(0)
    set_steering(0)
    time.sleep(0.5)

    #print(f"\n{'=' * 50}", file=sys.stderr)
    print(f"\n DRIVING FORWARD FOR {duration} SECONDS", file=sys.stderr)
    #print(f"{'=' * 50}\n", file=sys.stderr)

    #Drive Forward for 2 Seconds
    if CONFIDENCE_THRESHOLD >= 0.90:
        set_throttle(25)
        time.sleep(2)
    elif CONFIDENCE_THRESHOLD >= 0.80:
        set_throttle(0)


    #print(f"\n{'=' * 50}", file=sys.stderr)
    print("\n DRIVE SEQUENCE COMPLETE - STOPPED", file=sys.stderr)
    #print(f"{'=' * 50}\n", file=sys.stderr)


def main():
    """
    Read animal detection data (JSON) from stdin and control car.
    Usage: python3 live_animal_classifier2.py --mode console | python3 Car_Controller.py
    """
    print("Car controller started. Waiting for animal detections...", file=sys.stderr)
    print(f"Confidence threshold: {CONFIDENCE_THRESHOLD}", file=sys.stderr)
    print(f"Drive duration: {DRIVE_DURATION}s\n", file=sys.stderr)

    try:
        for line in sys.stdin:
            try:
                data = json.loads(line.strip())

                # Check if animal detected with high confidence
                if data['status'] == 'animal_detected':
                    confidence = data['confidence']

                    if confidence >= CONFIDENCE_THRESHOLD:
                        print(f"\nANIMAL CONFIRMED! Confidence: {confidence:.1%}", file=sys.stderr)
                        drive_forward(DRIVE_DURATION)
                    else:
                        print(f"Animal detected but confidence too low: {confidence:.1%}", file=sys.stderr)
                else:
                    # No animal or low confidence
                    pass  # Do nothing

            except json.JSONDecodeError:
                print(f"Invalid JSON: {line}", file=sys.stderr)
            except KeyError as e:
                print(f"Missing key in JSON: {e}", file=sys.stderr)

    except KeyboardInterrupt:
        print("\n\nController stopped", file=sys.stderr)


if __name__ == "__main__":
    main()