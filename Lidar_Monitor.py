import sys
import re
import json
import math

# --- Configuration ---
MIN_QUALITY = 10
CHANGE_THRESHOLD = 150 
BASELINE_FILE = 'room_baseline.json'

def trigger_cnn_model(x, y, distance, obs_type):
    """
    This is the specific function you requested to be called 
    to pass data to your CNN model.
    """
    print(f"!!! TRIGGERING CNN: {obs_type} at X:{x} Y:{y} (Dist: {distance}mm)")
    # Your CNN model logic goes here

def parse_lidar_line(line):
    match = re.search(r'theta:\s*([\d.]+)\s+Dist:\s*([\d.]+)\s+Q:\s*(\d+)', line)
    if match:
        return {'theta': float(match.group(1)), 'distance': float(match.group(2)), 'quality': int(match.group(3))}
    return None

def monitor_stream(baseline):
    print("Monitoring for obstructions...")
    for line in sys.stdin:
        p = parse_lidar_line(line)
        if p and p['quality'] >= MIN_QUALITY:
            angle_rad = math.radians(p['theta'])
            x = p['distance'] * math.cos(angle_rad)
            y = p['distance'] * math.sin(angle_rad)
            
            grid_key = f"{int(x // 50) * 50},{int(y // 50) * 50}"

            # Check against baseline
            if grid_key not in baseline:
                # 1. New object in empty space
                trigger_cnn_model(round(x, 2), round(y, 2), p['distance'], "NEW_OBJECT")
            
            elif (baseline[grid_key] - p['distance']) > CHANGE_THRESHOLD:
                # 2. Object is significantly closer than the wall/baseline
                trigger_cnn_model(round(x, 2), round(y, 2), p['distance'], "MOVED_OBJECT")

if __name__ == "__main__":
    try:
        with open(BASELINE_FILE, 'r') as f:
            baseline_data = json.load(f)
        monitor_stream(baseline_data)
    except FileNotFoundError:
        print(f"Error: {BASELINE_FILE} not found. Run lidar_mapper.py first.")
    except KeyboardInterrupt:
        sys.exit(0)