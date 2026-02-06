import sys
import re
import json
import math
# Configuration
MIN_DISTANCE = 100  # mm
MAX_DISTANCE = 3000  # mm
MIN_QUALITY = 10


def parse_lidar_line(line):
    """Parse a line of lidar output into structured data"""
    # Match pattern: "theta: 310.92 Dist: 00159.00 Q: 47"
    # Distance is in mm, theta is in degrees
    match = re.search(r'theta:\s*([\d.]+)\s+Dist:\s*([\d.]+)\s+Q:\s*(\d+)', line)
    if match:
        return {
            'theta': float(match.group(1)),
            'distance': float(match.group(2)),
            'quality': int(match.group(3)),
            'is_new_scan': line.strip().startswith('S')
        }
    return None


def process_scan(scan_data):
    """
    Process a complete scan and find the target.
    Returns JSON with target info.
    """
    # Filter valid points
    valid_points = [
        p for p in scan_data
        if p['quality'] >= MIN_QUALITY
           and MIN_DISTANCE <= p['distance'] <= MAX_DISTANCE
    ]

    if not valid_points:
        return {'status': 'no_target', 'valid_points': 0}

    # Find closest point
    closest = min(valid_points, key=lambda p: p['distance'])

    return {
        'status': 'target_found',
        'angle': closest['theta'],
        'distance': closest['distance'],
        'quality': closest['quality'],
        'valid_points': len(valid_points),
        'total_points': len(scan_data)
    }
def pull_into_map(total_json):
    hash_dict = {}
    if isinstance(total_json, str):
        data = json.loads(total_json)
    else:
        data = total_json
    angle = data.get("angle")
    if angle is None:
        print("null value")
        return
    distance = data.get("distance")
    #print(angle, distance)
    angle_rad = math.radians(angle)
    x = distance * math.cos(angle_rad)
    y = distance * math.sin(angle_rad)
    if x > 0 and y > 0:
        print("Quadrant 1")
    elif x < 0 and y > 0:
        print("Quadrant 2")
    elif x < 0 and y < 0:
        print("Quadrant 3")
    elif x > 0 and y < 0:
        print("Quadrant 4")
    print(x,y)
    #print("angle:", data.get("angle"))
    #print("distance:", data.get("distance"))    
def main():
    """
    Read lidar data from stdin, process complete scans, output JSON.
    Usage: python3 lidar_client.py | python3 lidar_processor.py
    """
    scan_data = []

#    print("Lidar processor started. Waiting for data...", file=sys.stderr)

    try:
        for line in sys.stdin:
            point = parse_lidar_line(line.strip())

            if point:
                # Check if this is a new scan
                if point['is_new_scan'] and len(scan_data) > 0:
                    # Process the complete scan
                    result = process_scan(scan_data)
                    #print(json.dumps(result))
                    total_json = json.dumps(result)
                    pull_into_map(total_json)
                    sys.stdout.flush()

                    # Start new scan
                    scan_data = []

                scan_data.append(point)

    except KeyboardInterrupt:
        print("\nProcessor stopped", file=sys.stderr)


if __name__ == "__main__":
    main()
