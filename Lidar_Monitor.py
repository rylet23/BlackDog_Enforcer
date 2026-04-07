import sys
import re
import json
import math
import Car_Controller
from obstruction_handler import ObstructionHandler

# --- Configuration ---
MIN_QUALITY = 10
CHANGE_THRESHOLD = 150
BASELINE_FILE = 'room_baseline.json'
CLUSTER_THRESHOLD = 100  # Max distance (mm) between points to be in the same "island"
MIN_POINTS_PER_OBJECT = 3  # Ignore noise (1 or 2 stray points)


def trigger_cnn_model(object_data):
    """
    Triggers once per clustered object.
    object_data contains: avg_x, avg_y, width, height, point_count
    """
    print(f"!!! OBJECT DETECTED: {object_data['type']} !!!")
    print(f"Location: ({object_data['x']}, {object_data['y']}) | Size: {object_data['w']}x{object_data['h']}mm")
    # Your CNN model logic goes here


# Initialize obstruction handler with car controller
obstruction_handler = ObstructionHandler(Car_Controller)


def get_clusters(points):
    """Simple distance-based clustering (Friend-of-friend)"""
    clusters = []
    for p in points:
        found_cluster = False
        for c in clusters:
            dist = math.sqrt((p['x'] - c['centroid_x']) ** 2 + (p['y'] - c['centroid_y']) ** 2)
            if dist < CLUSTER_THRESHOLD:
                c['points'].append(p)
                # Update centroid (running average)
                n = len(c['points'])
                c['centroid_x'] = ((c['centroid_x'] * (n - 1)) + p['x']) / n
                c['centroid_y'] = ((c['centroid_y'] * (n - 1)) + p['y']) / n
                found_cluster = True
                break
        if not found_cluster:
            clusters.append({'centroid_x': p['x'], 'centroid_y': p['y'], 'points': [p]})
    return clusters


def monitor_stream(baseline):
    print("Monitoring for objects (islands)...")
    current_scan_points = []
    last_theta = 0

    for line in sys.stdin:
        match = re.search(r'theta:\s*([\d.]+)\s+Dist:\s*([\d.]+)\s+Q:\s*(\d+)', line)
        if not match: continue

        theta = float(match.group(1))
        dist = float(match.group(2))
        qual = int(match.group(3))

        # Check if we've completed a full rotation (360 -> 0)
        if theta < last_theta:
            # FIX: pass baseline into process_frame so it's in scope
            process_frame(current_scan_points, baseline)
            current_scan_points = []

        last_theta = theta

        if qual >= MIN_QUALITY:
            if not (100 <= dist <= 500): 
                continue
            rad = math.radians(theta)
            x = dist * math.cos(rad)
            y = dist * math.sin(rad)
            grid_key = f"{int(x // 50) * 50},{int(y // 50) * 50}"

            # Filter: Is this point actually an obstruction?
            is_obs = False
            if grid_key not in baseline:
                is_obs = True
            elif (baseline[grid_key] - dist) > CHANGE_THRESHOLD:
                is_obs = True

            if is_obs:
                # FIX: store grid_key alongside each point so process_frame can use it
                current_scan_points.append({'x': x, 'y': y, 'dist': dist, 'grid_key': grid_key})


# FIX: accept baseline as a parameter
def process_frame(points, baseline):
    if not points: return

    clusters = get_clusters(points)

    for c in clusters:
        if len(c['points']) >= MIN_POINTS_PER_OBJECT:
            # Calculate Bounding Box
            xs = [p['x'] for p in c['points']]
            ys = [p['y'] for p in c['points']]

            obj_payload = {
                'x': round(c['centroid_x'], 2),
                'y': round(c['centroid_y'], 2),
                'w': round(max(xs) - min(xs), 2),
                'h': round(max(ys) - min(ys), 2),
                'count': len(c['points']),
                'type': "DETECTED_ISLAND"
            }
            trigger_cnn_model(obj_payload)

            # Determine obstruction type per point and notify handler
            # FIX: use p['dist'] (not p['distance']) and p['grid_key'] from the stored point data
            for p in c['points']:
                grid_key = p['grid_key']
                if grid_key not in baseline:
                    # New object in empty space
                    obstruction_handler.handle_obstruction(
                        round(p['x'], 2), round(p['y'], 2), p['dist'], "NEW_OBJECT"
                    )
                elif (baseline[grid_key] - p['dist']) > CHANGE_THRESHOLD:
                    # Object significantly closer than baseline
                    obstruction_handler.handle_obstruction(
                        round(p['x'], 2), round(p['y'], 2), p['dist'], "MOVED_OBJECT"
                    )


if __name__ == "__main__":
    try:
        with open(BASELINE_FILE, 'r') as f:
            baseline_data = json.load(f)
        monitor_stream(baseline_data)
    except FileNotFoundError:
        print(f"Error: {BASELINE_FILE} not found.")