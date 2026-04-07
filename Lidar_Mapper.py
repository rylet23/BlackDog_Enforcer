import sys
import re
import json
import math

# --- Configuration ---
MIN_DISTANCE = 100
MAX_DISTANCE = 500
MIN_QUALITY = 10
GRID_SIZE = 50 

baseline_grid = {}


def parse_lidar_line(line):
    match = re.search(r'theta:\s*([\d.]+)\s+Dist:\s*([\d.]+)\s+Q:\s*(\d+)', line)
    if match:
        return {
            'theta': float(match.group(1)),
            'distance': float(match.group(2)),
            'quality': int(match.group(3)),
            'is_new_scan': line.strip().startswith('S')
        }
    return None

def build_baseline(scan_data):
    global baseline_grid
    valid_points = [p for p in scan_data if p['quality'] >= MIN_QUALITY and MIN_DISTANCE <= p['distance'] <= MAX_DISTANCE]
    
    for p in valid_points:
        angle_rad = math.radians(p['theta'])
        x = p['distance'] * math.cos(angle_rad)
        y = p['distance'] * math.sin(angle_rad)
        
        # Grid key as string for JSON compatibility
        grid_key = f"{int(x // GRID_SIZE) * GRID_SIZE},{int(y // GRID_SIZE) * GRID_SIZE}"
        
        if grid_key in baseline_grid:
            baseline_grid[grid_key] = min(baseline_grid[grid_key], p['distance'])
        else:
            baseline_grid[grid_key] = p['distance']

def run_mapper():
    current_scan = []
    print("Mapping environment... Press Ctrl+C to save and exit.")
    for line in sys.stdin:
        data = parse_lidar_line(line)
        if data:
            if data['is_new_scan'] and current_scan:
                build_baseline(current_scan)
                current_scan = []
            current_scan.append(data)

if __name__ == "__main__":
    try:
        run_mapper()
    except KeyboardInterrupt:
        with open('room_baseline.json', 'w') as f:
            json.dump(baseline_grid, f, indent=4)
        print(f"\nSUCCESS: Baseline saved with {len(baseline_grid)} points.")
        sys.exit(0)