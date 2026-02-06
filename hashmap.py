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
MIN_DISTANCE = 100  #in mm. Equal to 0.1m 
MAX_DISTANCE = 3000  #in mm. Equal to 3m
MIN_QUALITY = 10

# Map configuration
GRID_RESOLUTION = 50  # mm per cell (smaller = more detailed, larger = less memory)
MAP_SIZE = 200  # cells in each direction (200 * 50mm = 10m x 10m map)

#TODO Need to change this so robot starts on outside of the Hashmap. 
ROBOT_X = MAP_SIZE // 2  # Robot starts at center
ROBOT_Y = MAP_SIZE // 2


class OccupancyGrid:
    """2D occupancy grid map"""
    
    def __init__(self, size, resolution):
        """
        Initialize the occupancy grid.
        
        Args:
            size: Grid size (will be size x size)
            resolution: Resolution in mm per cell
        """
        self.size = size
        self.resolution = resolution
        
        # Grid stores probability of occupancy (0-100)
        # -1 = unknown, 0 = free, 100 = occupied
        self.grid = np.full((size, size), -1, dtype=np.int8)
        
        # Hit and miss counts for probabilistic updates
        self.hits = np.zeros((size, size), dtype=np.int32)
        self.misses = np.zeros((size, size), dtype=np.int32)
        
        self.robot_x = ROBOT_X
        self.robot_y = ROBOT_Y
    
    def world_to_grid(self, x_mm, y_mm):
        """Convert world coordinates (mm) to grid coordinates"""
        grid_x = int(self.robot_x + (x_mm / self.resolution))
        grid_y = int(self.robot_y + (y_mm / self.resolution))
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x, grid_y):
        """Convert grid coordinates to world coordinates (mm)"""
        x_mm = (grid_x - self.robot_x) * self.resolution
        y_mm = (grid_y - self.robot_y) * self.resolution
        return x_mm, y_mm
    
    def is_valid(self, grid_x, grid_y):
        """Check if grid coordinates are valid"""
        return 0 <= grid_x < self.size and 0 <= grid_y < self.size
    
    def bresenham_line(self, x0, y0, x1, y1):
        """
        Get all cells along a line using Bresenham's algorithm.
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
        Update the occupancy grid with a complete LIDAR scan.
        
        Args:
            scan_points: List of dicts with 'theta', 'distance', 'quality'
        """
        robot_grid_x = self.robot_x
        robot_grid_y = self.robot_y
        
        for point in scan_points:
            if point['quality'] < MIN_QUALITY:
                continue
            if not (MIN_DISTANCE <= point['distance'] <= MAX_DISTANCE):
                continue
            
            # Convert polar to Cartesian (LIDAR reference frame)
            theta_rad = math.radians(point['theta'])
            x_mm = point['distance'] * math.cos(theta_rad)
            y_mm = point['distance'] * math.sin(theta_rad)
            
            # Convert to grid coordinates
            end_x, end_y = self.world_to_grid(x_mm, y_mm)
            
            if not self.is_valid(end_x, end_y):
                continue
            
            # Mark all cells along the ray as free
            ray_cells = self.bresenham_line(robot_grid_x, robot_grid_y, end_x, end_y)
            
            # Update all cells except the last one (the obstacle)
            for i, (cell_x, cell_y) in enumerate(ray_cells[:-1]):
                if self.is_valid(cell_x, cell_y):
                    self.misses[cell_x, cell_y] += 1
            
            # Mark the endpoint as occupied
            if self.is_valid(end_x, end_y):
                self.hits[end_x, end_y] += 1
    
    def update_probabilities(self):
        """Update grid probabilities based on hits and misses"""
        for x in range(self.size):
            for y in range(self.size):
                total = self.hits[x, y] + self.misses[x, y]
                if total > 0:
                    # Calculate occupancy probability
                    prob = (self.hits[x, y] / total) * 100
                    self.grid[x, y] = int(prob)
    
    def get_grid_dict(self):
        """
        Return grid as a dictionary mapping (x, y) -> occupancy value.
        Only returns cells that have been observed.
        """
        grid_dict = {}
        for x in range(self.size):
            for y in range(self.size):
                if self.grid[x, y] != -1:
                    grid_dict[(x, y)] = int(self.grid[x, y])
        return grid_dict
    
    def get_ascii_map(self, width=80, height=40):
        """
        Generate ASCII representation of the map for visualization.
        
        Args:
            width: Width in characters
            height: Height in characters
        """
        # Calculate which part of the grid to display
        center_x, center_y = self.robot_x, self.robot_y
        
        # Scale factor
        scale_x = self.size / width
        scale_y = self.size / height
        
        lines = []
        for row in range(height):
            line = []
            grid_y = int(row * scale_y)
            
            for col in range(width):
                grid_x = int(col * scale_x)
                
                # Check if this is robot position
                if abs(grid_x - self.robot_x) < 2 and abs(grid_y - self.robot_y) < 2:
                    line.append('R')
                elif not self.is_valid(grid_x, grid_y):
                    line.append('?')
                else:
                    value = self.grid[grid_x, grid_y]
                    if value == -1:
                        line.append(' ')  # Unknown
                    elif value < 30:
                        line.append('.')  # Free
                    elif value < 70:
                        line.append('o')  # Uncertain
                    else:
                        line.append('#')  # Occupied
            
            lines.append(''.join(line))
        
        return '\n'.join(lines)
    
    def export_json(self):
        """Export grid as JSON for external use"""
        return {
            'size': self.size,
            'resolution_mm': self.resolution,
            'robot_position': {'x': self.robot_x, 'y': self.robot_y},
            'occupied_cells': [
                {'x': x, 'y': y, 'probability': int(self.grid[x, y])}
                for x in range(self.size)
                for y in range(self.size)
                if self.grid[x, y] >= 70  # Only export high-confidence occupied cells
            ],
            'free_cells_count': int(np.sum((self.grid >= 0) & (self.grid < 30))),
            'occupied_cells_count': int(np.sum(self.grid >= 70)),
            'unknown_cells_count': int(np.sum(self.grid == -1))
        }


def parse_lidar_line(line):
    """Parse a line of LIDAR output into structured data"""
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
    """
    Read LIDAR data from stdin, build 2D occupancy grid map.
    Usage: python3 client.py | python3 lidar_mapper.py
    """
    # Create occupancy grid
    grid = OccupancyGrid(MAP_SIZE, GRID_RESOLUTION)
    
    scan_data = []
    scan_count = 0
    
    print("LIDAR Mapper started. Building 2D occupancy grid...", file=sys.stderr)
    print(f"Map size: {MAP_SIZE}x{MAP_SIZE} cells, Resolution: {GRID_RESOLUTION}mm/cell", file=sys.stderr)
    print(f"Coverage area: {MAP_SIZE * GRID_RESOLUTION / 1000:.1f}m x {MAP_SIZE * GRID_RESOLUTION / 1000:.1f}m", file=sys.stderr)
    print("", file=sys.stderr)
    
    try:
        for line in sys.stdin:
            point = parse_lidar_line(line.strip())
            
            if point:
                # Check if this is a new scan
                if point['is_new_scan'] and len(scan_data) > 0:
                    # Update grid with complete scan
                    grid.update_with_scan(scan_data)
                    grid.update_probabilities()
                    
                    scan_count += 1
                    
                    # Output status every 10 scans
                    if scan_count % 10 == 0:
                        result = {
                            'scan_count': scan_count,
                            'points_in_scan': len(scan_data),
                            'map_stats': grid.export_json()
                        }
                        print(json.dumps(result))
                        sys.stdout.flush()
                        
                        # Print ASCII map to stderr for debugging
                        if scan_count % 50 == 0:
                            print(f"\n=== Map Update (Scan #{scan_count}) ===", file=sys.stderr)
                            print(grid.get_ascii_map(60, 30), file=sys.stderr)
                            print("", file=sys.stderr)
                    
                    # Start new scan
                    scan_data = []
                
                scan_data.append(point)
        
    except KeyboardInterrupt:
        print("\nStopping mapper...", file=sys.stderr)
        
        # Final map export
        print("\n=== Final Map ===", file=sys.stderr)
        print(grid.get_ascii_map(80, 40), file=sys.stderr)
        
        final_result = {
            'status': 'final',
            'total_scans': scan_count,
            'map': grid.export_json(),
            'grid_dict': grid.get_grid_dict()
        }
        
 #       print("\nFinal map data:", file=sys.stderr)
#        print(json.dumps(final_result, indent=2))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
