from weni import Tool
from weni.context import Context
from weni.responses import TextResponse

from PIL import Image, ImageDraw, ImageFont
import os
from math import sqrt
import json
import os
import base64
import requests
import numpy as np
import heapq
from math import sqrt
from typing import List, Tuple
from dataclasses import dataclass
from collections import defaultdict
import traceback


class BoothNavigatorObstacles:
    def __init__(self, obstacles_file="vtex_obstacles.json", map_image="artifacts/vtex_day_map.png"):
        """Initialize the booth navigator with obstacle-based pathfinding"""
        self.map_image_path = map_image
        self.obstacles_file = obstacles_file
        
        # Get image dimensions
        if os.path.exists(self.map_image_path):
            with Image.open(self.map_image_path) as img:
                self.img_width, self.img_height = img.size
        else:
            self.img_width, self.img_height = 8000, 5000
        
        # Initialize pathfinder
        self.pathfinder = ObstaclePathfinder(self.img_width, self.img_height, obstacles_file)
        
        # PDF to PNG transformation parameters (if needed)
        self.scale_factor = 2.0
    
    def find_booth(self, booth_name):
        """Find a booth by name"""
        location = self.pathfinder.get_booth_location(booth_name)
        if location:
            # Find the actual booth name that was matched
            actual_name = booth_name
            for obstacle in self.pathfinder.obstacles:
                if obstacle.category == 'booth':
                    cx = (obstacle.x1 + obstacle.x2) / 2
                    cy = (obstacle.y1 + obstacle.y2) / 2
                    if abs(cx - location[0]) < 1 and abs(cy - location[1]) < 1:
                        actual_name = obstacle.name
                        break
            
            return {
                'name': actual_name,
                'x': location[0],
                'y': location[1]
            }
        return None
    
    def find_path(self, from_booth, to_booth):
        """Find the path between two booths using obstacle avoidance"""
        # Find booth locations
        start = self.find_booth(from_booth)
        end = self.find_booth(to_booth)
        
        if start is None:
            raise ValueError(f"Booth '{from_booth}' not found")
        if end is None:
            raise ValueError(f"Booth '{to_booth}' not found")
        
        # Find path using obstacle pathfinder
        path_coords = self.pathfinder.find_path(start['x'], start['y'], end['x'], end['y'])
        path_names = [start['name'], end['name']]
        
        return path_coords, path_names
    
    def draw_route(self, from_booth, to_booth, output_file="route_map.png", show_debug=False):
        """Draw the route on the map and return as bytes"""
        import io
        
        # Helper function to draw Waze-style arrow
        def draw_waze_arrow(draw, x, y, dx_norm, dy_norm, size, color):
            """Draw a clean Waze-style navigation arrow"""
            # Arrow tip
            tip_x = x + dx_norm * size * 0.5
            tip_y = y + dy_norm * size * 0.5
            
            # Arrow base center
            base_x = x - dx_norm * size * 0.3
            base_y = y - dy_norm * size * 0.3
            
            # Perpendicular vectors for arrow width
            perp_dx = -dy_norm * size * 0.35
            perp_dy = dx_norm * size * 0.35
            
            # Arrow points - clean triangular shape
            arrow_points = [
                (tip_x, tip_y),  # Tip
                (base_x + perp_dx, base_y + perp_dy),  # Left base
                (x - dx_norm * size * 0.1, y - dy_norm * size * 0.1),  # Back indent
                (base_x - perp_dx, base_y - perp_dy),  # Right base
            ]
            
            # Draw the arrow with gradient effect
            if len(color) == 4 and color[3] > 100:  # Main arrow, not shadow
                # Create gradient effect by drawing multiple layers
                for i in range(3):
                    layer_alpha = color[3] - i * 30
                    layer_color = (color[0] + i * 20, color[1] + i * 10, color[2], layer_alpha)
                    offset = i * 0.5
                    layer_points = [
                        (p[0] - dx_norm * offset, p[1] - dy_norm * offset) 
                        for p in arrow_points
                    ]
                    draw.polygon(layer_points, fill=layer_color)
            else:
                # Shadow or single color
                draw.polygon(arrow_points, fill=color)
        
        # Find the path
        path_coords, path_names = self.find_path(from_booth, to_booth)
        
        # Load the base map
        if not os.path.exists(self.map_image_path):
            raise FileNotFoundError(f"Map image not found: {self.map_image_path}")
        
        img = Image.open(self.map_image_path).convert("RGBA")
        
        # Create overlay for drawing
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Draw obstacles if in debug mode
        if show_debug:
            for obstacle in self.pathfinder.obstacles:
                color = {
                    'booth': (255, 182, 193, 50),  # Light pink
                    'wall': (211, 211, 211, 50),    # Light gray
                    'stage': (152, 251, 152, 50),   # Light green
                    'obstacle': (240, 230, 140, 50), # Khaki
                    'empty': (200, 200, 200, 30)     # Very light gray
                }.get(obstacle.category, (224, 224, 224, 50))
                
                draw.rectangle(
                    [obstacle.x1, obstacle.y1, obstacle.x2, obstacle.y2],
                    fill=color,
                    outline=(100, 100, 100, 100),
                    width=1
                )
        
        # Get start and end positions
        start_x, start_y = path_coords[0]
        end_x, end_y = path_coords[-1]
        
        # Draw path segments with smooth curves
        if len(path_coords) > 1:
            # Draw the path line with a glow effect
            for width, alpha in [(8, 50), (5, 100), (3, 200)]:
                for i in range(len(path_coords) - 1):
                    draw.line(
                        [path_coords[i], path_coords[i + 1]],
                        fill=(91, 192, 235, alpha),
                        width=width
                    )
        
        # Draw directional arrows along the path
        if len(path_coords) > 2:
            # Calculate total path length
            total_length = 0
            segments = []
            
            for i in range(len(path_coords) - 1):
                x1, y1 = path_coords[i]
                x2, y2 = path_coords[i + 1]
                dx = x2 - x1
                dy = y2 - y1
                length = (dx**2 + dy**2)**0.5
                
                if length > 0:
                    segments.append({
                        'start': (x1, y1),
                        'end': (x2, y2),
                        'length': length,
                        'start_distance': total_length,
                        'dx_norm': dx / length,
                        'dy_norm': dy / length
                    })
                    total_length += length
            
            # Place arrows along the path
            arrow_spacing = 150  # Spacing between arrows
            arrow_size = 40      # Arrow size
            min_start_distance = 100  # Distance from start for first arrow
            min_end_distance = 100    # Distance from end for last arrow
            
            # Calculate arrow positions
            current_dist = min_start_distance
            
            while current_dist < total_length - min_end_distance:
                # Find which segment contains this distance
                for seg in segments:
                    if seg['start_distance'] <= current_dist < seg['start_distance'] + seg['length']:
                        # Calculate position along segment
                        t = (current_dist - seg['start_distance']) / seg['length']
                        arrow_x = seg['start'][0] + t * (seg['end'][0] - seg['start'][0])
                        arrow_y = seg['start'][1] + t * (seg['end'][1] - seg['start'][1])
                        
                        # Draw shadow
                        shadow_offset = 2
                        draw_waze_arrow(draw, arrow_x + shadow_offset, arrow_y + shadow_offset, 
                                      seg['dx_norm'], seg['dy_norm'], arrow_size, 
                                      (0, 0, 0, 30))
                        
                        # Draw arrow
                        draw_waze_arrow(draw, arrow_x, arrow_y, seg['dx_norm'], seg['dy_norm'], 
                                      arrow_size, (91, 192, 235, 255))
                        break
                
                current_dist += arrow_spacing
        
        # Move markers up to avoid covering booth names
        marker_offset_y = -80  # Offset for markers
        
        # Draw Point A marker - modern design
        # Pulsing circle effect
        for radius in [35, 25, 15]:
            alpha = 100 + (35 - radius) * 4
            draw.ellipse((start_x-radius, start_y-radius+marker_offset_y, 
                         start_x+radius, start_y+radius+marker_offset_y), 
                        fill=(0, 255, 100, alpha), outline=None)
        
        # Inner solid circle
        draw.ellipse((start_x-12, start_y-12+marker_offset_y, 
                     start_x+12, start_y+12+marker_offset_y), 
                    fill=(0, 200, 80, 255), outline=(255, 255, 255, 255), width=3)
        
        # Draw Point B marker - modern design
        # Pulsing circle effect
        for radius in [35, 25, 15]:
            alpha = 100 + (35 - radius) * 4
            draw.ellipse((end_x-radius, end_y-radius+marker_offset_y, 
                         end_x+radius, end_y+radius+marker_offset_y), 
                        fill=(255, 80, 80, alpha), outline=None)
        
        # Inner solid circle
        draw.ellipse((end_x-12, end_y-12+marker_offset_y, 
                     end_x+12, end_y+12+marker_offset_y), 
                    fill=(220, 60, 60, 255), outline=(255, 255, 255, 255), width=3)
        
        # Draw connecting lines from markers to actual positions
        # Start position indicator - elegant dotted line
        for i in range(0, int(abs(marker_offset_y) - 35), 8):
            y_pos = start_y + marker_offset_y + 35 + i
            draw.ellipse((start_x-2, y_pos-2, start_x+2, y_pos+2), 
                        fill=(0, 200, 80, 150))
        
        # End position indicator - elegant dotted line
        for i in range(0, int(abs(marker_offset_y) - 35), 8):
            y_pos = end_y + marker_offset_y + 35 + i
            draw.ellipse((end_x-2, y_pos-2, end_x+2, y_pos+2), 
                        fill=(220, 60, 60, 150))
        
        # Load font for labels
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
            font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
        except:
            font = ImageFont.load_default()
            font_bold = font
        
        # Draw floating labels with modern style
        # Point A label - Portuguese
        label_a = "Você está aqui"
        bbox_a = draw.textbbox((start_x - 70, start_y - 85 + marker_offset_y - 20), label_a, font=font)
        # Rounded rectangle background
        padding = 10
        draw.rounded_rectangle(
            [(bbox_a[0] - padding, bbox_a[1] - padding), 
             (bbox_a[2] + padding, bbox_a[3] + padding)],
            radius=12,
            fill=(0, 200, 80, 240),
            outline=(255, 255, 255, 255),
            width=2
        )
        draw.text((start_x - 70, start_y - 85 + marker_offset_y - 20), label_a, 
                 fill=(255, 255, 255, 255), font=font)
        
        # Point B label - Portuguese
        label_b = "Seu destino"
        bbox_b = draw.textbbox((end_x - 55, end_y - 85 + marker_offset_y - 20), label_b, font=font)
        draw.rounded_rectangle(
            [(bbox_b[0] - padding, bbox_b[1] - padding), 
             (bbox_b[2] + padding, bbox_b[3] + padding)],
            radius=12,
            fill=(220, 60, 60, 240),
            outline=(255, 255, 255, 255),
            width=2
        )
        draw.text((end_x - 55, end_y - 85 + marker_offset_y - 20), label_b, 
                 fill=(255, 255, 255, 255), font=font)
        
        # Add route information box
        info_text = f"De: {path_names[0]}\nPara: {path_names[1]}"
        if len(path_coords) > 2:
            info_text += f"\n{len(path_coords)-1} pontos de navegação"
        
        info_bbox = draw.textbbox((20, 20), info_text, font=font)
        draw.rounded_rectangle(
            [(10, 10), (info_bbox[2] + 30, info_bbox[3] + 30)],
            radius=10,
            fill=(255, 255, 255, 240),
            outline=(91, 192, 235, 255),
            width=2
        )
        draw.text((20, 20), info_text, fill=(50, 50, 50, 255), font=font)
        
        # Composite the overlay onto the base image
        img = Image.alpha_composite(img, overlay)
        
        # Crop the image to focus on the route area
        # Calculate bounding box with padding
        all_x = [coord[0] for coord in path_coords]
        all_y = [coord[1] for coord in path_coords]
        
        # Include marker positions in bounding box calculation
        all_y.extend([start_y + marker_offset_y - 100, end_y + marker_offset_y - 100])
        
        min_x = max(0, min(all_x) - 300)
        max_x = min(img.width, max(all_x) + 300)
        min_y = max(0, min(all_y) - 200)
        max_y = min(img.height, max(all_y) + 200)
        
        # Ensure minimum size
        width = max_x - min_x
        height = max_y - min_y
        min_dimension = 1000
        
        if width < min_dimension:
            center_x = (min_x + max_x) // 2
            min_x = max(0, center_x - min_dimension // 2)
            max_x = min(img.width, center_x + min_dimension // 2)
        
        if height < min_dimension:
            center_y = (min_y + max_y) // 2
            min_y = max(0, center_y - min_dimension // 2)
            max_y = min(img.height, center_y + min_dimension // 2)
        
        # Crop the image
        img_cropped = img.crop((int(min_x), int(min_y), int(max_x), int(max_y)))
        
        # Add a subtle border to the cropped image
        border_img = Image.new('RGBA', 
                              (img_cropped.width + 20, img_cropped.height + 20), 
                              (240, 240, 240, 255))
        border_img.paste(img_cropped, (10, 10))
        
        # Save to bytes buffer instead of file
        img_bytes = io.BytesIO()
        border_img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        
        return img_bytes, path_names
    
    def list_booths(self):
        """List all available booths"""
        booths = []
        for obstacle in self.pathfinder.obstacles:
            if obstacle.category == 'booth':
                booths.append(obstacle.name)
        return sorted(booths)
    
    def export_debug_visualization(self, output_file="debug_obstacles.png"):
        """Export a debug visualization showing all obstacles"""
        self.pathfinder.visualize_path([], output_file)
        return output_file


@dataclass
class Point:
    x: float
    y: float
    
    def __hash__(self):
        return hash((self.x, self.y))
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def distance_to(self, other):
        return sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

@dataclass
class Rectangle:
    x1: float
    y1: float
    x2: float
    y2: float
    name: str
    category: str
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside this rectangle"""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2
    
    def intersects_line(self, p1: Point, p2: Point) -> bool:
        """Check if a line segment intersects this rectangle"""
        # Check if either endpoint is inside the rectangle
        if self.contains_point(p1.x, p1.y) or self.contains_point(p2.x, p2.y):
            return True
        
        # Check line-rectangle intersection
        return self._line_intersects_rect(p1.x, p1.y, p2.x, p2.y)
    
    def _line_intersects_rect(self, x1, y1, x2, y2) -> bool:
        """Check if a line segment intersects a rectangle"""
        # Check if line is completely outside rectangle bounds
        if (max(x1, x2) < self.x1 or min(x1, x2) > self.x2 or
            max(y1, y2) < self.y1 or min(y1, y2) > self.y2):
            return False
        
        # Check intersection with each edge of the rectangle
        edges = [
            (self.x1, self.y1, self.x2, self.y1),  # Top
            (self.x2, self.y1, self.x2, self.y2),  # Right
            (self.x2, self.y2, self.x1, self.y2),  # Bottom
            (self.x1, self.y2, self.x1, self.y1),  # Left
        ]
        
        for ex1, ey1, ex2, ey2 in edges:
            if self._lines_intersect(x1, y1, x2, y2, ex1, ey1, ex2, ey2):
                return True
        
        return False
    
    def _lines_intersect(self, x1, y1, x2, y2, x3, y3, x4, y4) -> bool:
        """Check if two line segments intersect"""
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return False
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        return 0 <= t <= 1 and 0 <= u <= 1
    
    def get_corners(self, padding: float = 0) -> List[Point]:
        """Get the corners of the rectangle with optional padding"""
        return [
            Point(self.x1 - padding, self.y1 - padding),
            Point(self.x2 + padding, self.y1 - padding),
            Point(self.x2 + padding, self.y2 + padding),
            Point(self.x1 - padding, self.y2 + padding)
        ]

class ObstaclePathfinder:
    def __init__(self, map_width: int, map_height: int, obstacles_file: str = None):
        """Initialize the pathfinder with obstacles"""
        self.map_width = map_width
        self.map_height = map_height
        self.obstacles = []
        self.visibility_graph = None
        self.corner_padding = 20  # Padding around obstacle corners
        
        self.load_obstacles(obstacles_file)
    
    def load_obstacles(self, filename: str):
        """Load obstacles from a project file"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, filename)
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        self.obstacles = []
        for rect_data in data.get('rectangles', []):
            # Skip certain categories that might not be actual obstacles
            if rect_data.get('category') in ['entrance', 'exit']:
                continue
                
            rect = Rectangle(
                rect_data['x1'],
                rect_data['y1'],
                rect_data['x2'],
                rect_data['y2'],
                rect_data.get('name', ''),
                rect_data.get('category', 'obstacle')
            )
            self.obstacles.append(rect)
        
        # Build visibility graph after loading obstacles
        self._build_visibility_graph()
    
    def _build_visibility_graph(self):
        """Build a visibility graph connecting all obstacle corners"""
        # Collect all corner points
        corner_points = []
        for obstacle in self.obstacles:
            corners = obstacle.get_corners(self.corner_padding)
            for corner in corners:
                # Only add corners that are within map bounds and not inside any obstacle
                if (0 <= corner.x <= self.map_width and 
                    0 <= corner.y <= self.map_height and
                    not self._point_in_any_obstacle(corner)):
                    corner_points.append(corner)
        
        # Build graph connecting visible corners
        self.visibility_graph = defaultdict(list)
        
        for i, p1 in enumerate(corner_points):
            for j, p2 in enumerate(corner_points):
                if i != j and self._is_path_clear(p1, p2):
                    distance = p1.distance_to(p2)
                    self.visibility_graph[p1].append((p2, distance))
    
    def _point_in_any_obstacle(self, point: Point) -> bool:
        """Check if a point is inside any obstacle"""
        for obstacle in self.obstacles:
            if obstacle.contains_point(point.x, point.y):
                return True
        return False
    
    def _is_path_clear(self, p1: Point, p2: Point) -> bool:
        """Check if a path between two points is clear of obstacles"""
        for obstacle in self.obstacles:
            if obstacle.intersects_line(p1, p2):
                return False
        return True
    
    def _find_nearest_clear_point(self, point: Point) -> Point:
        """Find the nearest clear point if the given point is inside an obstacle"""
        # Check if point is already clear
        if not self._point_in_any_obstacle(point):
            return point
        
        # Find which obstacle contains the point
        containing_obstacle = None
        for obstacle in self.obstacles:
            if obstacle.contains_point(point.x, point.y):
                containing_obstacle = obstacle
                break
        
        if not containing_obstacle:
            return point
        
        # Find the nearest edge of the obstacle
        edges = [
            # Top edge
            (point.x, containing_obstacle.y1 - self.corner_padding),
            # Bottom edge
            (point.x, containing_obstacle.y2 + self.corner_padding),
            # Left edge
            (containing_obstacle.x1 - self.corner_padding, point.y),
            # Right edge
            (containing_obstacle.x2 + self.corner_padding, point.y),
            # Corners
            (containing_obstacle.x1 - self.corner_padding, containing_obstacle.y1 - self.corner_padding),
            (containing_obstacle.x2 + self.corner_padding, containing_obstacle.y1 - self.corner_padding),
            (containing_obstacle.x1 - self.corner_padding, containing_obstacle.y2 + self.corner_padding),
            (containing_obstacle.x2 + self.corner_padding, containing_obstacle.y2 + self.corner_padding),
        ]
        
        # Find the nearest clear point
        best_point = None
        best_distance = float('inf')
        
        for x, y in edges:
            # Check if point is within map bounds
            if 0 <= x <= self.map_width and 0 <= y <= self.map_height:
                test_point = Point(x, y)
                # Check if point is clear
                if not self._point_in_any_obstacle(test_point):
                    distance = point.distance_to(test_point)
                    if distance < best_distance:
                        best_distance = distance
                        best_point = test_point
        
        # If we found a clear point, return it; otherwise return original
        return best_point if best_point else point
    
    def find_path(self, start_x: float, start_y: float, end_x: float, end_y: float) -> List[Tuple[float, float]]:
        """Find the shortest path avoiding obstacles"""
        start = Point(start_x, start_y)
        end = Point(end_x, end_y)
        
        # If start or end points are inside obstacles, move them to the nearest clear position
        start_clear = self._find_nearest_clear_point(start)
        end_clear = self._find_nearest_clear_point(end)
        
        # Check if direct path is possible
        if self._is_path_clear(start_clear, end_clear):
            return [(start_clear.x, start_clear.y), (end_clear.x, end_clear.y)]
        
        # Use A* algorithm on visibility graph
        path_points = self._astar_search(start_clear, end_clear)
        
        if path_points:
            # Smooth the path
            smoothed = self._smooth_path(path_points)
            # Add original start and end points if they were adjusted
            result = []
            if start != start_clear:
                result.append((start.x, start.y))
            result.extend([(p.x, p.y) for p in smoothed])
            if end != end_clear:
                result.append((end.x, end.y))
            return result
        
        # If no path found, return direct path as fallback
        return [(start.x, start.y), (end.x, end.y)]
    
    def _astar_search(self, start: Point, goal: Point) -> List[Point]:
        """A* search algorithm on visibility graph"""
        # Create temporary graph including start and goal
        temp_graph = defaultdict(list, self.visibility_graph)
        
        # Add connections from start to visible corners
        for corner in self.visibility_graph.keys():
            if self._is_path_clear(start, corner):
                distance = start.distance_to(corner)
                temp_graph[start].append((corner, distance))
                temp_graph[corner].append((start, distance))
        
        # Add connections from goal to visible corners
        for corner in self.visibility_graph.keys():
            if self._is_path_clear(goal, corner):
                distance = goal.distance_to(corner)
                temp_graph[goal].append((corner, distance))
                temp_graph[corner].append((goal, distance))
        
        # Add direct connection if possible
        if self._is_path_clear(start, goal):
            distance = start.distance_to(goal)
            temp_graph[start].append((goal, distance))
        
        # A* algorithm
        open_set = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: start.distance_to(goal)}
        
        while open_set:
            current_f, current = heapq.heappop(open_set)
            
            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                path.reverse()
                return path
            
            for neighbor, distance in temp_graph[current]:
                tentative_g = g_score[current] + distance
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + neighbor.distance_to(goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        return []  # No path found
    
    def _smooth_path(self, path: List[Point]) -> List[Point]:
        """Smooth the path by removing unnecessary waypoints"""
        if len(path) <= 2:
            return path
        
        smoothed = [path[0]]
        i = 0
        
        while i < len(path) - 1:
            # Try to skip ahead as far as possible
            j = len(path) - 1
            while j > i + 1:
                if self._is_path_clear(path[i], path[j]):
                    break
                j -= 1
            
            smoothed.append(path[j])
            i = j
        
        return smoothed
    
    def visualize_path(self, path: List[Tuple[float, float]], output_file: str = "path_debug.png"):
        """Visualize the path and obstacles for debugging"""
        # Create a white image
        img = Image.new('RGB', (self.map_width, self.map_height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw obstacles
        for obstacle in self.obstacles:
            color = {
                'booth': '#FFB6C1',
                'wall': '#D3D3D3',
                'stage': '#98FB98',
                'obstacle': '#F0E68C'
            }.get(obstacle.category, '#E0E0E0')
            
            draw.rectangle(
                [obstacle.x1, obstacle.y1, obstacle.x2, obstacle.y2],
                fill=color,
                outline='black',
                width=2
            )
            
            # Draw obstacle name
            cx = (obstacle.x1 + obstacle.x2) / 2
            cy = (obstacle.y1 + obstacle.y2) / 2
            draw.text((cx, cy), obstacle.name, fill='black', anchor='mm')
        
        # Draw visibility graph (optional, for debugging)
        if self.visibility_graph:
            for point, neighbors in self.visibility_graph.items():
                for neighbor, _ in neighbors:
                    draw.line(
                        [(point.x, point.y), (neighbor.x, neighbor.y)],
                        fill='lightgray',
                        width=1
                    )
        
        # Draw path
        if len(path) > 1:
            for i in range(len(path) - 1):
                draw.line(
                    [path[i], path[i + 1]],
                    fill='blue',
                    width=3
                )
            
            # Draw waypoints
            for point in path:
                draw.ellipse(
                    [point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5],
                    fill='red',
                    outline='darkred'
                )
        
        img.save(output_file)
        return output_file
    
    def get_booth_location(self, booth_name: str) -> Tuple[float, float]:
        """Get the location of a booth by name"""
        booth_name_lower = booth_name.lower()
        
        # First try exact match (case-insensitive)
        for obstacle in self.obstacles:
            if obstacle.category == 'booth' and obstacle.name.lower() == booth_name_lower:
                # Return center of booth
                cx = (obstacle.x1 + obstacle.x2) / 2
                cy = (obstacle.y1 + obstacle.y2) / 2
                return (cx, cy)
        
        # Try partial match - prioritize matches at the beginning
        best_match = None
        best_match_score = float('inf')
        
        for obstacle in self.obstacles:
            if obstacle.category == 'booth':
                obstacle_name_lower = obstacle.name.lower()
                if booth_name_lower in obstacle_name_lower:
                    # Score based on position of match (lower is better)
                    score = obstacle_name_lower.find(booth_name_lower)
                    if score < best_match_score:
                        best_match = obstacle
                        best_match_score = score
        
        if best_match:
            cx = (best_match.x1 + best_match.x2) / 2
            cy = (best_match.y1 + best_match.y2) / 2
            return (cx, cy)
        
        return None

def create_navigation_grid(width: int, height: int, obstacles: List[Rectangle], 
                         grid_size: int = 10) -> np.ndarray:
    """Create a navigation grid for alternative pathfinding"""
    # Create grid (1 = walkable, 0 = obstacle)
    grid_width = width // grid_size
    grid_height = height // grid_size
    grid = np.ones((grid_height, grid_width), dtype=np.uint8)
    
    # Mark obstacles in grid
    for obstacle in obstacles:
        x1 = max(0, int(obstacle.x1 // grid_size))
        y1 = max(0, int(obstacle.y1 // grid_size))
        x2 = min(grid_width - 1, int(obstacle.x2 // grid_size))
        y2 = min(grid_height - 1, int(obstacle.y2 // grid_size))
        
        grid[y1:y2+1, x1:x2+1] = 0
    
    return grid


class CreateBoothMap(Tool):
    
    def upload_to_imgur(self, img_bytes, context):
        """Upload image to Imgur and return the URL"""
        # Get Imgur client ID from credentials
        imgur_client_id = context.credentials.get("imgur_client_id")
        
        if not imgur_client_id:
            # If no Imgur credentials, use a default anonymous client ID
            # This is a public client ID for anonymous uploads
            imgur_client_id = "a5c2e47b3c6f07d"
        
        # Reset buffer position
        img_bytes.seek(0)
        
        # Convert to base64
        img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')
        
        # Imgur API endpoint
        url = "https://api.imgur.com/3/image"
        
        headers = {
            "Authorization": f"Client-ID {imgur_client_id}"
        }
        
        data = {
            "image": img_base64,
            "type": "base64",
            "title": "VTEX Day Route Map",
            "description": "Route map generated for VTEX Day event navigation"
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get("success"):
                return result["data"]["link"]
            else:
                raise Exception(f"Imgur upload failed: {result.get('data', {}).get('error', 'Unknown error')}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to upload image to Imgur: {str(e)}")
    
    def send_whatsapp_message(self, image_url, context):
        """Send the route map image to the user via WhatsApp"""
        # Get parameters from context
        project_uuid = context.parameters.get("project_uuid")
        contact_id = context.parameters.get("contact_id")
        
        # Get credentials from context
        project_token = context.credentials.get("project_token")
        
        if not project_uuid or not contact_id:
            raise Exception("Missing required parameters: project_uuid and contact_id")
        
        if not project_token:
            raise Exception("Missing required credential: project_token")
        
        # Weni WhatsApp API endpoint
        url = "https://flows.weni.ai/api/v2/whatsapp_broadcasts.json"
        
        headers = {
            "Authorization": f"Token {project_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "urns": [contact_id],
            "project": project_uuid,
            "msg": {
                "text": "Aqui está a sua rota ☝️",
                "attachments": [f"image/png:{image_url}"]
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to send WhatsApp message: {str(e)}")
    
    def execute(self, context: Context) -> TextResponse:
        from_booth = context.parameters.get("starting_booth")
        to_booth = context.parameters.get("destination_booth")
        obstacles_file = "project.json"

        print(f"BOOTH MAP: {from_booth} to {to_booth}")

        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            map_image = os.path.join(current_dir, "vtex_day_map.png")

            navigator = BoothNavigatorObstacles(obstacles_file=obstacles_file, map_image=map_image)
            img_bytes, path_names = navigator.draw_route(
                    from_booth,
                    to_booth,
                    "route_map.png",  # This is just for reference, not actually saved
                    show_debug=False
            )
        
            image_url = self.upload_to_imgur(img_bytes, context)
            
            # Send via WhatsApp
            whatsapp_response = None
            try:
                whatsapp_response = self.send_whatsapp_message(image_url, context)
                whatsapp_status = "Message sent successfully via WhatsApp"
            except Exception as e:
                traceback.print_exc()
                whatsapp_status = f"WhatsApp delivery failed: {str(e)}"
            
            return TextResponse(data={
                "message": f"Route map from {from_booth} to {to_booth} has been generated successfully",
                "whatsapp_status": whatsapp_status,
                "whatsapp_response": whatsapp_response
            })
        except Exception as e:
            traceback.print_exc()
            return TextResponse(data={
                "message": "Failed to generate the route map image and send it to the user"
            })