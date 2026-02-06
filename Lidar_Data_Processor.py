import sys
import re
import json
import math

# Configuration
MIN_DISTANCE = 100  # mm
MAX_DISTANCE = 3000  # mm
MIN_QUALITY = 10

baseline_grid = {}
is_calibrated = False

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
    global baseline_grid, is_calibrated
    
    # Filter valid points
    valid_points = [
        p for p in scan_data
        if p['quality'] >= MIN_QUALITY
           and MIN_DISTANCE <= p['distance'] <= MAX_DISTANCE
    ]

    if not valid_points:
        return # [ Read 112 lines ]

    current_grid = {}

    for p in valid_points:
        angle = p['theta']
        distance = p['distance']
        
        if angle == 0:
            print("null value")
        
        print(angle, distance)
        
        angle_rad = math.radians(angle)
        x = distance * math.cos(angle_rad)
        y = distance * math.sin(angle_rad)
        
        print(x, y)

        if x > 0 and y > 0:
            print("Quadrant 1")
        elif x < 0 and y > 0:
            print("Quadrant 2")
        elif x < 0 and y < 0:
            print("Quadrant 3")
        elif x > 0 and y < 0:
            print("Quadrant 4")

        grid_key = (int(x // 50) * 50, int(y // 50) * 50)
        current_grid[grid_key] = distance

    if not is_calibrated:
        baseline_grid = current_grid
        is_calibrated = True
        print("--- BASELINE CREATED ---")
        return

    for coord, dist in current_grid.items():
        if coord not in baseline_grid:
            print(f"DIFFERENCE DETECTED: New object at {coord}")
        elif abs(dist - baseline_grid[coord]) > 150:
            print(f"DIFFERENCE DETECTED: Movement at {coord}")

def run_lidar_monitor():
    current_scan = []
    for line in sys.stdin:
        data = parse_lidar_line(line)
        if data:
            if data['is_new_scan'] and current_scan:
                process_scan(current_scan)
                current_scan = []
            current_scan.append(data)

if __name__ == "__main__":
    run_lidar_monitor()