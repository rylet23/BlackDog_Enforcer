#!/usr/bin/env python3
"""
Map Utilities
Helper functions for loading, comparing, and working with baseline maps.
"""

import pickle
import json
import numpy as np


def load_baseline_map(filepath):
    """
    Load a baseline map from file.
    
    Args:
        filepath: Path to the baseline map file (.pkl)
    
    Returns:
        dict with 'hashmap', 'metadata', 'grid', 'hits', 'misses'
    """
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    return data


def compare_maps(baseline_hashmap, current_hashmap, threshold=40):
    """
    Compare two hashmaps to find differences (potential obstructions).
    
    Args:
        baseline_hashmap: Reference map {(x, y): occupancy}
        current_hashmap: Current map {(x, y): occupancy}
        threshold: Minimum occupancy difference to consider significant
    
    Returns:
        dict with 'new_obstacles', 'removed_obstacles', 'changed_cells'
    """
    new_obstacles = []
    removed_obstacles = []
    changed_cells = []
    
    # Check all cells in current map
    for pos, current_val in current_hashmap.items():
        baseline_val = baseline_hashmap.get(pos, -1)
        
        if baseline_val == -1:
            # Cell not in baseline (unexplored in baseline)
            if current_val >= 70:
                new_obstacles.append({'position': pos, 'occupancy': current_val})
        else:
            # Calculate difference
            diff = current_val - baseline_val
            
            if abs(diff) >= threshold:
                changed_cells.append({
                    'position': pos,
                    'baseline': baseline_val,
                    'current': current_val,
                    'difference': diff
                })
                
                # New obstacle (was free, now occupied)
                if baseline_val < 30 and current_val >= 70:
                    new_obstacles.append({
                        'position': pos,
                        'baseline': baseline_val,
                        'current': current_val
                    })
                # Removed obstacle (was occupied, now free)
                elif baseline_val >= 70 and current_val < 30:
                    removed_obstacles.append({
                        'position': pos,
                        'baseline': baseline_val,
                        'current': current_val
                    })
    
    return {
        'new_obstacles': new_obstacles,
        'removed_obstacles': removed_obstacles,
        'changed_cells': changed_cells,
        'total_changes': len(changed_cells)
    }


def get_map_stats(hashmap):
    """Get statistics about a map"""
    if not hashmap:
        return {'total_cells': 0, 'free': 0, 'occupied': 0, 'uncertain': 0}
    
    values = list(hashmap.values())
    return {
        'total_cells': len(values),
        'free': sum(1 for v in values if 0 <= v < 30),
        'occupied': sum(1 for v in values if v >= 70),
        'uncertain': sum(1 for v in values if 30 <= v < 70)
    }


def hashmap_to_grid(hashmap, size):
    """
    Convert hashmap back to numpy grid.
    
    Args:
        hashmap: {(x, y): occupancy}
        size: Grid size
    
    Returns:
        numpy array (size x size)
    """
    grid = np.full((size, size), -1, dtype=np.int8)
    for (x, y), value in hashmap.items():
        if 0 <= x < size and 0 <= y < size:
            grid[x, y] = value
    return grid


def find_closest_obstacle(hashmap, lidar_x, lidar_y, min_occupancy=70):
    """
    Find the closest obstacle to a given position.
    
    Args:
        hashmap: {(x, y): occupancy}
        lidar_x: LIDAR X position
        lidar_y: LIDAR Y position
        min_occupancy: Minimum occupancy to consider as obstacle
    
    Returns:
        dict with 'position', 'distance', 'occupancy' or None
    """
    obstacles = [(pos, occ) for pos, occ in hashmap.items() if occ >= min_occupancy]
    
    if not obstacles:
        return None
    
    closest = min(obstacles, key=lambda item: 
                  (item[0][0] - lidar_x)**2 + (item[0][1] - lidar_y)**2)
    
    pos, occ = closest
    distance = np.sqrt((pos[0] - lidar_x)**2 + (pos[1] - lidar_y)**2)
    
    return {
        'position': pos,
        'distance': distance,
        'occupancy': occ
    }


def export_map_json(hashmap, metadata, filepath):
    """Export map to human-readable JSON"""
    hashmap_serializable = {f"{x},{y}": v for (x, y), v in hashmap.items()}
    
    data = {
        'hashmap': hashmap_serializable,
        'metadata': metadata,
        'stats': get_map_stats(hashmap)
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
