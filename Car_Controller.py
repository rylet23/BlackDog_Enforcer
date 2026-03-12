import sys
import json
import time
import select
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
esc.start(7.5)    # Start at neutral immediately
steer.start(7.5)  # Start at neutral immediately

# Configuration
CONFIDENCE_THRESHOLD = 0.90
DRIVE_DURATION = 2.0  # seconds
COOLDOWN_DURATION = 3.0  # seconds to ignore detections after a drive

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
    set_throttle(25)
    time.sleep(duration)
    set_throttle(0)  # STOP the car

    #print(f"\n{'=' * 50}", file=sys.stderr)
    print("\n DRIVE SEQUENCE COMPLETE - STOPPED", file=sys.stderr)
    #print(f"{'=' * 50}\n", file=sys.stderr)


def drain_stdin_buffer():
    """Discard any messages that piled up in the pipe while we were driving."""
    drained = 0
    while True:
        ready = select.select([sys.stdin], [], [], 0)[0]
        if not ready:
            break
        line = sys.stdin.readline()
        if not line:
            break
        drained += 1
    if drained:
        print(f"Drained {drained} stale message(s) from buffer", file=sys.stderr)



def main():
    """
    Read animal detection data (JSON) from stdin and control car.
    Usage: python3 live_animal_classifier2.py --mode console | python3 Car_Controller.py
    """
    print("Car controller started. Waiting for animal detections...", file=sys.stderr)
    print(f"Confidence threshold: {CONFIDENCE_THRESHOLD}", file=sys.stderr)
    print(f"Drive duration: {DRIVE_DURATION}s", file=sys.stderr)
    print(f"Cooldown duration: {COOLDOWN_DURATION}s\n", file=sys.stderr)

    last_drive_time = 0  # epoch 0 means no cooldown on startup

    try:
        for line in sys.stdin:
            try:
                data = json.loads(line.strip())

                # Check if animal detected with high confidence
                if data['status'] == 'animal_detected':
                    confidence = data['confidence']

                    if confidence >= CONFIDENCE_THRESHOLD:
                        # Enforce cooldown — skip if we drove too recently
                        time_since_last_drive = time.time() - last_drive_time
                        if time_since_last_drive < COOLDOWN_DURATION:
                            remaining = COOLDOWN_DURATION - time_since_last_drive
                            print(f"Cooldown active — ignoring detection ({remaining:.1f}s remaining)", file=sys.stderr)
                        else:
                            print(f"\nANIMAL CONFIRMED! Confidence: {confidence:.1%}", file=sys.stderr)
                            drive_forward(DRIVE_DURATION)
                            last_drive_time = time.time()
                            drain_stdin_buffer()  # Discard messages that buffered during the drive
                    else:
                        print(f"Animal detected but confidence too low: {confidence:.1%}", file=sys.stderr)
                else:
                    pass  # No animal — do nothing

            except json.JSONDecodeError:
                print(f"Invalid JSON: {line}", file=sys.stderr)
            except KeyError as e:
                print(f"Missing key in JSON: {e}", file=sys.stderr)

    except KeyboardInterrupt:
        print("\n\nController stopped", file=sys.stderr)
    finally:
        # Clean shutdown
        set_throttle(0)
        set_steering(0)
        esc.stop()
        steer.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    main()