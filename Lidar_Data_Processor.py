import sys
import re
import json
import math

#shshsh
# --- Configuration ---
MIN_DISTANCE = 100  # mm
MAX_DISTANCE = 12000  # mm
MIN_QUALITY = 10
GRID_SIZE = 50 # mm (Size of the grid squares)
CHANGE_THRESHOLD = 150 # mm (How much depth change constitutes an obstruction)

baseline_grid = {}
is_calibrated = False

def parse_lidar_line(line):
    """Parse a line of lidar output into structured data"""
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
    Process a complete scan, compare to baseline, and map obstructions.
    """
    global baseline_grid, is_calibrated

    # 1. Filter valid points
    valid_points = [
        p for p in scan_data
        if p['quality'] >= MIN_QUALITY
        and MIN_DISTANCE <= p['distance'] <= MAX_DISTANCE
    ]

    if not valid_points:
        return

    # 2. Map current scan to grid
    current_grid = {}
    
    for p in valid_points:
        angle = p['theta']
        distance = p['distance']

        # Convert Polar (Angle/Dist) to Cartesian (X/Y)
        angle_rad = math.radians(angle)
        x = distance * math.cos(angle_rad)
        y = distance * math.sin(angle_rad)

        # Snap coordinates to grid (e.g., round to nearest 50mm)
        # We use a tuple (x, y) as the dictionary key
        grid_key = (int(x // GRID_SIZE) * GRID_SIZE, int(y // GRID_SIZE) * GRID_SIZE)
        
        # Store distance. Note: This overwrites if multiple points hit the same cell.
        # Ideally, you might want to store the 'min' distance for safety.
        if grid_key in current_grid:
            current_grid[grid_key] = min(current_grid[grid_key], distance)
        else:
            current_grid[grid_key] = distance

    # 3. Calibration: If first run, set baseline and exit
    if not is_calibrated:
        baseline_grid = current_grid
        is_calibrated = True
        print(json.dumps({"status": "CALIBRATED", "baseline_points": len(baseline_grid)}))
        return

    # 4. Detect Obstructions
    # This hash map stores only the problem areas
    obstruction_map = {}

    for coord, dist in current_grid.items():
        # Case A: Object detected where baseline was empty
        if MIN_DISTANCE <= dist <= MAX_DISTANCE:
            if coord not in baseline_grid:
                obstruction_map[str(coord)] = {
                    "x": coord[0], 
                    "y": coord[1], 
                    "dist": dist, 
                    "type": "NEW_OBJECT"
                }
            
            # Case B: Object detected, but distance is significantly different (closer or further)
            elif abs(dist - baseline_grid[coord]) > CHANGE_THRESHOLD:
                obstruction_map[str(coord)] = {
                    "x": coord[0], 
                    "y": coord[1], 
                    "dist": dist, 
                    "delta": round(dist - baseline_grid[coord], 2),
                    "type": "MOVED_OBJECT"
                }

    # 5. Output the Obstruction Map
    # We print valid JSON so another program can read this output easily
    if obstruction_map:
        output = {
            "status": "OBSTRUCTION_DETECTED",
            "count": len(obstruction_map),
            "obstructions": obstruction_map
        }
        print(json.dumps(output))
    else:
        # Optional: Heartbeat to show system is running but clear
        # print(json.dumps({"status": "CLEAR"}))
        pass

def run_lidar_monitor():
    current_scan = []
    # Read from standard input (pipe)
    for line in sys.stdin:
        data = parse_lidar_line(line)
        if data:
            if data['is_new_scan'] and current_scan:
                process_scan(current_scan)
                current_scan = []
            current_scan.append(data)


if __name__ == "__main__":
    try:
        run_lidar_monitor()
    except KeyboardInterrupt:
        sys.exit(0)
