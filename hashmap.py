
#!/usr/bin/env python3
"""
Baseline Map Creator
Creates a reference occupancy grid map from LIDAR data.
"""

import sys
import re
import json
import pickle
import numpy as np
import math
from datetime import datetime
import argparse
import signal

# Configuration
MIN_DISTANCE = 100  # mm
MAX_DISTANCE = 3000  # mm
MIN_QUALITY = 10

# Map configuration
GRID_RESOLUTION = 50  # mm per cell
MAP_SIZE = 200  # cells in each direction (10m x 10m)

# LIDAR position - edge of map since robot starts outside
LIDAR_X = 10  # Near left edge
LIDAR_Y = MAP_SIZE // 2  # Centered vertically

# Global for signal handling
baseline_map = None
output_file = 'baseline_map.pkl'
save_json = False


class BaselineMap:
    """2D occupancy grid for baseline/reference map"""
    
    def __init__(self, size, resolution, lidar_x, lidar_y):
        ""
        self.size = size
        self.resolution = resolution
        self.lidar_x = lidar_x
        self.lidar_y = lidar_y
        
        self.grid = np.full((size, size), -1, dtype=np.int8)
        self.hits = np.zeros((size, size), dtype=np.int32)
        self.misses = np.zeros((size, size), dtype=np.int32)
        
        self.creation_time = datetime.now().isoformat()
        self.scan_count = 0
    
    def world_to_grid(self, x_mm, y_mm):
        """Convert world coordinates (mm) to grid coordinates"""
        grid_x = int(self.lidar_x + (x_mm / self.resolution))
        grid_y = int(self.lidar_y + (y_mm / self.resolution))
        return grid_x, grid_y
    
    def is_valid(self, grid_x, grid_y):
        """Check if grid coordinates are valid"""
        return 0 <= grid_x < self.size and 0 <= grid_y < self.size
    
    def bresenham_line(self, x0, y0, x1, y1):
        """Bresenham's line algorithm"""
        cells = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        x, y = x0, y0
        
        while True:
            cells.append((x, y))
            if x == x1 and y == y1:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return cells
    
    def update_with_scan(self, scan_points):
        """Update the map with a complete LIDAR scan"""
        valid_points = 0
        
        for point in scan_points:
            if point['quality'] < MIN_QUALITY:
                continue
            if not (MIN_DISTANCE <= point['distance'] <= MAX_DISTANCE):
                continue
            
            valid_points += 1
            
            # Convert polar to Cartesian
            theta_rad = math.radians(point['theta'])
            x_mm = point['distance'] * math.cos(theta_rad)
            y_mm = point['distance'] * math.sin(theta_rad)
            
            # Convert to grid coordinates
            end_x, end_y = self.world_to_grid(x_mm, y_mm)
            
            if not self.is_valid(end_x, end_y):
                continue
            
            # Ray trace from LIDAR to obstacle
            ray_cells = self.bresenham_line(self.lidar_x, self.lidar_y, end_x, end_y)
            
            # Mark ray path as free space
            for cell_x, cell_y in ray_cells[:-1]:
                if self.is_valid(cell_x, cell_y):
                    self.misses[cell_x, cell_y] += 1
            
            # Mark endpoint as occupied
            if self.is_valid(end_x, end_y):
                self.hits[end_x, end_y] += 1
        
        self.scan_count += 1
        return valid_points
    
    def finalize_probabilities(self):
        """Calculate final occupancy probabilities"""
        for x in range(self.size):
            for y in range(self.size):
                total = self.hits[x, y] + self.misses[x, y]
                if total > 0:
                    prob = (self.hits[x, y] / total) * 100
                    self.grid[x, y] = int(prob)
    
    def to_hashmap(self):
        """Convert to hashmap: {(x, y): occupancy_value}"""
        hashmap = {}
        for x in range(self.size):
            for y in range(self.size):
                if self.grid[x, y] != -1:
                    hashmap[(x, y)] = int(self.grid[x, y])
        return hashmap
    
    def get_metadata(self):
        """Get map metadata"""
        return {
            'creation_time': self.creation_time,
            'size': self.size,
            'resolution_mm': self.resolution,
            'lidar_position': {'x': self.lidar_x, 'y': self.lidar_y},
            'scan_count': self.scan_count,
            'observed_cells': int(np.sum(self.grid != -1)),
            'free_cells': int(np.sum((self.grid >= 0) & (self.grid < 30))),
            'occupied_cells': int(np.sum(self.grid >= 70)),
            'uncertain_cells': int(np.sum((self.grid >= 30) & (self.grid < 70)))
        }
    
    def save(self, filepath):
        """Save baseline map to file"""
        data = {
            'hashmap': self.to_hashmap(),
            'metadata': self.get_metadata(),
            'grid': self.grid,
            'hits': self.hits,
            'misses': self.misses
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"\n✓ Baseline map saved to: {filepath}", file=sys.stderr)
        return filepath
    
    def save_json(self, filepath):
        """Save baseline map to JSON"""
        hashmap = self.to_hashmap()
        hashmap_serializable = {f"{x},{y}": v for (x, y), v in hashmap.items()}
        
        data = {
            'hashmap': hashmap_serializable,
            'metadata': self.get_metadata()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ JSON map saved to: {filepath}", file=sys.stderr)


def parse_lidar_line(line):
    """Parse LIDAR data line"""
    match = re.search(r'theta:\s*([\d.]+)\s+Dist:\s*([\d.]+)\s+Q:\s*(\d+)', line)
    if match:
        return {
            'theta': float(match.group(1)),
            'distance': float(match.group(2)),
            'quality': int(match.group(3)),
            'is_new_scan': line.strip().startswith('S')
        }
    return None


def save_and_exit(signum=None, frame=None):
    """Signal handler to save map on Ctrl+C"""
    global baseline_map, output_file, save_json
    
    if baseline_map and baseline_map.scan_count > 0:
        print("\n\n" + "=" * 60, file=sys.stderr)
        print("Saving baseline map...", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        
        baseline_map.finalize_probabilities()
        baseline_map.save(output_file)
        
        if save_json:
            json_path = output_file.replace('.pkl', '.json')
            baseline_map.save_json(json_path)
        
        metadata = baseline_map.get_metadata()
        print("\n" + "=" * 60, file=sys.stderr)
        print("BASELINE MAP SUMMARY", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"Scans collected: {metadata['scan_count']}", file=sys.stderr)
        print(f"Observed cells: {metadata['observed_cells']}", file=sys.stderr)
        print(f"Free space: {metadata['free_cells']} cells", file=sys.stderr)
        print(f"Occupied: {metadata['occupied_cells']} cells", file=sys.stderr)
        print(f"Uncertain: {metadata['uncertain_cells']} cells", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
    else:
        print("\nNo data collected yet!", file=sys.stderr)
    
    sys.exit(0)


def main():
    global baseline_map, output_file, save_json
    
    parser = argparse.ArgumentParser(description='Create baseline LIDAR map')
    parser.add_argument('-o', '--output', default='baseline_map.pkl',
                        help='Output file path (default: baseline_map.pkl)')
    parser.add_argument('-n', '--num-scans', type=int, default=0,
                        help='Number of scans to collect (0 = run until Ctrl+C)')
    parser.add_argument('--json', action='store_true',
                        help='Also save as JSON file')
    parser.add_argument('--resolution', type=int, default=GRID_RESOLUTION,
                        help=f'Grid resolution in mm (default: {GRID_RESOLUTION})')
    parser.add_argument('--map-size', type=int, default=MAP_SIZE,
                        help=f'Map size in cells (default: {MAP_SIZE})')
    
    args = parser.parse_args()
    
    output_file = args.output
    save_json = args.json
    
    # Set up signal handler for graceful exit
    signal.signal(signal.SIGINT, save_and_exit)
    signal.signal(signal.SIGTERM, save_and_exit)
    
    # Create baseline map
    baseline_map = BaselineMap(args.map_size, args.resolution, LIDAR_X, LIDAR_Y)
    
    scan_data = []
    target_scans = args.num_scans
    
    print("=" * 60, file=sys.stderr)
    print("BASELINE MAP CREATOR", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Map size: {args.map_size}x{args.map_size} cells", file=sys.stderr)
    print(f"Resolution: {args.resolution}mm/cell", file=sys.stderr)
    print(f"Coverage: {args.map_size * args.resolution / 1000:.1f}m x {args.map_size * args.resolution / 1000:.1f}m", file=sys.stderr)
    print(f"LIDAR position: ({LIDAR_X}, {LIDAR_Y})", file=sys.stderr)
    
    if target_scans > 0:
        print(f"Target scans: {target_scans}", file=sys.stderr)
    else:
        print("Mode: Continuous (press Ctrl+C to save and exit)", file=sys.stderr)
    
    print("=" * 60, file=sys.stderr)
    print("\nWaiting for LIDAR data...", file=sys.stderr)
    
    lines_received = 0
    
    try:
        for line in sys.stdin:
            lines_received += 1
            
            # Debug: show we're receiving data
            if lines_received == 1:
                print("✓ Receiving LIDAR data", file=sys.stderr)
            
            point = parse_lidar_line(line.strip())
            
            if point:
                # New scan marker
                if point['is_new_scan'] and len(scan_data) > 0:
                    valid_points = baseline_map.update_with_scan(scan_data)
                    
                    # Progress indicator
                    if baseline_map.scan_count == 1:
                        print(f"✓ First scan processed ({len(scan_data)} points, {valid_points} valid)", 
                              file=sys.stderr)
                    elif baseline_map.scan_count % 10 == 0:
                        if target_scans > 0:
                            progress = (baseline_map.scan_count / target_scans) * 100
                            print(f"Scan {baseline_map.scan_count}/{target_scans} ({progress:.1f}%) - {valid_points} valid points", 
                                  file=sys.stderr)
                        else:
                            print(f"Scan {baseline_map.scan_count} - {valid_points} valid points", 
                                  file=sys.stderr)
                    
                    # Check if we've collected enough scans
                    if target_scans > 0 and baseline_map.scan_count >= target_scans:
                        print(f"\n✓ Target scan count reached ({target_scans} scans)", file=sys.stderr)
                        save_and_exit()
                    
                    scan_data = []
                
                scan_data.append(point)
        
    except KeyboardInterrupt:
        save_and_exit()
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        save_and_exit()
    
    # If stdin ends naturally
    if baseline_map.scan_count > 0:
        save_and_exit()
    else:
        print("\nNo scans were collected!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
