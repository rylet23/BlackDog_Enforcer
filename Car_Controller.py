import sys
import json

# Configuration
STOP_DISTANCE = 200  # mm - stop if closer than this
FORWARD_ANGLE_RANGE = 30  # degrees - consider angles within ±30° as "forward"


def calculate_steering(angle):
    """
    Calculate steering direction based on target angle.
    Returns: 'forward', 'left', 'right', or 'backward'
    """
    # Normalize angle to -180 to 180 range
    if angle > 180:
        angle = angle - 360

    if abs(angle) <= FORWARD_ANGLE_RANGE:
        return 'forward'
    elif 90 <= abs(angle) <= 270:
        return 'backward'
    elif angle < 0:
        return 'left'
    else:
        return 'right'


def control_car(target_data):
    """
    Make driving decisions based on target data.
    """
    if target_data['status'] == 'no_target':
        print(f"No target detected. Valid points: {target_data['valid_points']}", file=sys.stderr)
        # TODO: Add your "search" behavior here
        # e.g., slowly rotate to scan for targets
        return

    angle = target_data['angle']
    distance = target_data['distance']

    print(f"Target: {angle:.1f}° at {distance:.1f}mm (Q:{target_data['quality']})", file=sys.stderr)

    # Decision logic
    if distance < STOP_DISTANCE:
        action = 'stop'
        print("  ACTION: STOP - Too close!", file=sys.stderr)
        # TODO: Add your stop code here
    else:
        direction = calculate_steering(angle)
        action = direction
        print(f"  ACTION: {direction.upper()}", file=sys.stderr)
        # TODO: Add your motor control code here
        # if direction == 'forward':
        #     # drive forward
        # elif direction == 'left':
        #     # turn left
        # elif direction == 'right':
        #     # turn right

    # Output action as JSON for potential logging/chaining
    output = {
        'action': action,
        'target_angle': angle,
        'target_distance': distance
    }
    print(json.dumps(output))
    sys.stdout.flush()


def main():
    """
    Read processed lidar data (JSON) from stdin and control car.
    Usage: ./ProcessAndClient.sh | python3 lidar_processor.py | python3 car_controller.py
    """
    print("Car controller started. Waiting for target data...", file=sys.stderr)

    try:
        for line in sys.stdin:
            try:
                target_data = json.loads(line.strip())
                control_car(target_data)
            except json.JSONDecodeError:
                print(f"Invalid JSON: {line}", file=sys.stderr)

    except KeyboardInterrupt:
        print("\nController stopped", file=sys.stderr)


if __name__ == "__main__":
    main()