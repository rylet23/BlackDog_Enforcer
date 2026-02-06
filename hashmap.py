#!/usr/bin/env python3
"""
Baseline Map Creator
Creates a reference occupancy grid map from LIDAR data.
This baseline will be saved and used later to detect changes/obstructions.
"""

import sys
import re
import json
import pickle
import numpy as np
import math
from datetime import datetime
import argparse

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


class BaselineMap:
    """2D occupancy grid for baseline/reference map"""
    
    def __init__(self, size, resolution, lidar_x, lidar_y):
        """
        Initialize the baseline map.
        
        Args:
            size: Grid size (will be size x size)
            resolution: Resolution in mm per cell
            lidar_x: LIDAR X position in grid coordinates
            lidar_y: LIDAR Y position in grid coordinates
        """
        self.size = size
        self.resolution = resolution
        self.lidar_x = lidar_x
        self.lidar_y = lidar_y
        
        # Grid stores probability of occupancy (0-100)
        # -1 = unknown, 0 = free, 100 = occupied
        self.grid = np.full((size, size), -1, dtype=np.int8)
        
        # Hit and miss counts for probabilistic updates
        self.hits = np.zeros((size, size), dtype=np.int32)
        self.misses = np.zeros((size, size), dtype=np.int32)
        
        # Metadata
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
        """
        Bresenham's line algorithm for ray tracing.
        Returns list of (x, y) tuples.
        """
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
        """
        Update the map with a complete LIDAR scan.
        
        Args:
            scan_points: List of dicts with 'theta', 'distance', 'quality'
        """
        valid_count = 0
        for point in scan_points:
            if point['quality'] < MIN_QUALITY:
                continue
            if not (MIN_DISTANCE <= point['distance'] <= MAX_DISTANCE):
                continue
            
            valid_count += 1
            
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
            
            # Mark ray path as free space (all cells except last)
            for cell_x, cell_y in ray_cells[:-1]:
                if self.is_valid(cell_x, cell_y):
                    self.misses[cell_x, cell_y] += 1
            
            # Mark endpoint as occupied
            if self.is_valid(end_x, end_y):
                self.hits[end_x, end_y] += 1
        
        self.scan_count += 1
        return valid_count
    
    def finalize_probabilities(self):
        """Calculate final occupancy probabilities"""
        for x in range(self.size):
            for y in range(self.size):
                total = self.hits[x, y] + self.misses[x, y]
                if total > 0:
                    prob = (self.hits[x, y] / total) * 100
                    self.grid[x, y] = int(prob)
    
    def to_hashmap(self):
        """
        Convert to hashmap: {(x, y): occupancy_value}
        Only includes observed cells.
        """
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
        """Save baseline map to file (pickle format)"""
        data = {
            'hashmap': self.to_hashmap(),
            'metadata': self.get_metadata(),
            'grid': self.grid,
            'hits': self.hits,
            'misses': self.misses
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"Saved: {filepath}", file=sys.stderr)
    
    def save_json(self, filepath):
        """Save baseline map to JSON file (for human readability)"""
        hashmap = self.to_hashmap()
        
        # Convert tuple keys to strings for JSON
        hashmap_serializable = {f"{x},{y}": v for (x, y), v in hashmap.items()}
        
        data = {
            'hashmap': hashmap_serializable,
            'metadata': self.get_metadata()
        }
        
        #with open(filepath, 'w') as f:
            #json.dump(data, f, indent=2)
    
    @staticmethod
    def load(filepath):
        """Load baseline map from file"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        return data


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


def main():
    parser = argparse.ArgumentParser(description='Create baseline LIDAR map')
    parser.add_argument('-o', '--output', default='baseline_map.pkl',
                        help='Output file path (default: baseline_map.pkl)')
    parser.add_argument('-n', '--num-scans', type=int, default=50,
                        help='Number of scans to collect (default: 50)')
    parser.add_argument('--json', action='store_true',
                        help='Also save as JSON file')
    parser.add_argument('--resolution', type=int, default=GRID_RESOLUTION,
                        help=f'Grid resolution in mm (default: {GRID_RESOLUTION})')
    parser.add_argument('--map-size', type=int, default=MAP_SIZE,
                        help=f'Map size in cells (default: {MAP_SIZE})')
    
    args = parser.parse_args()
    
    # Create baseline map
    baseline = BaselineMap(args.map_size, args.resolution, LIDAR_X, LIDAR_Y)
    
    scan_data = []
    target_scans = args.num_scans
    
    try:
        for line in sys.stdin:
            point = parse_lidar_line(line.strip())
            
            if point:
                # New scan marker
                if point['is_new_scan'] and len(scan_data) > 0:
                    baseline.update_with_scan(scan_data)
                    
                    # Progress indicator - only every 10 scans
                    if baseline.scan_count % 10 == 0:
                        # print(f"Scans: {baseline.scan_count}/{target_scans}", file=sys.stderr)
                        print("hello")
                    # Check if we've collected enough scans
                    if baseline.scan_count >= target_scans:
                        break
                    
                    scan_data = []
                
                scan_data.append(point)
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    
    # Only save if we have collected scans
    if baseline.scan_count > 0:
        baseline.finalize_probabilities()
        baseline.save(args.output)
        
        if args.json:
            json_path = args.output.replace('.pkl', '.json')
            baseline.save_json(json_path)
        
        # Output final count and location
        #print(f"Complete: {baseline.scan_count} scans", file=sys.stderr)
    else:
        print("Error: No scans collected", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
