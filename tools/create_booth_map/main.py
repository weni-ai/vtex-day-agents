from weni import Tool
from weni.context import Context
from weni.responses import TextResponse


import csv
import networkx as nx
from PIL import Image, ImageDraw, ImageFont
import sys
import os
from pathlib import Path
from math import sqrt
import json
import os
import io
import base64
import requests


class BoothData:
    """Simple class to handle booth data operations without pandas"""
    
    def __init__(self, csv_file):
        self.booths = []
        self._load_csv(csv_file)
    
    def _load_csv(self, csv_file):
        """Load booth data from CSV file"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, csv_file)

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Convert coordinates to float
                booth_data = {
                    'booth': row['booth'],
                    'x': float(row['x']),
                    'y': float(row['y']),
                    'booth_lower': row['booth'].lower()
                }
                self.booths.append(booth_data)
    
    def find_booth(self, booth_name):
        """Find a booth by name (case-insensitive)"""
        booth_lower = booth_name.lower()
        
        # Exact match first
        for booth in self.booths:
            if booth['booth_lower'] == booth_lower:
                return booth
        
        # Partial match if no exact match
        for booth in self.booths:
            if booth_lower in booth['booth_lower']:
                return booth
        
        return None
    
    def get_booth_names(self):
        """Get list of all booth names"""
        return [booth['booth'] for booth in self.booths]

class BoothNavigatorWalkable:
    def __init__(self, booths_csv="booths.csv", map_image="artifacts/vtex_day_map.png", use_walkable_paths=True):
        """Initialize the booth navigator with walkable pathfinding"""
        # Load booth locations
        self.booth_data = BoothData(booths_csv)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.map_image_path = os.path.join(current_dir, map_image)
        
        # Get image dimensions for coordinate transformation
        if os.path.exists(self.map_image_path):
            with Image.open(self.map_image_path) as img:
                self.img_width, self.img_height = img.size
        else:
            self.img_width, self.img_height = 8000, 5000
        
        # PDF to PNG transformation parameters
        self.scale_factor = 2.0
        
        # Check if coordinates need transformation
        max_y = max(booth['y'] for booth in self.booth_data.booths)
        if max_y < self.img_height / 2:
            self.needs_transformation = True
        else:
            self.needs_transformation = False
        
        # Initialize walkable pathfinder
        self.use_walkable_paths = use_walkable_paths
        if self.use_walkable_paths:
            try:
                self.pathfinder = WalkablePathfinder(map_image)
            except Exception as e:
                print(f"Warning: Could not initialize walkable pathfinder: {e}")
                self.use_walkable_paths = False
    
    def _transform_coordinates(self, x, y):
        """Transform PDF coordinates to PNG coordinates"""
        if self.needs_transformation:
            x_png = x * self.scale_factor
            y_png = y * self.scale_factor
            return x_png, y_png
        else:
            return x, y
    
    def find_booth(self, booth_name):
        """Find a booth by name (case-insensitive)"""
        return self.booth_data.find_booth(booth_name)
    
    def find_path(self, from_booth, to_booth):
        """Find the path between two booths using walkable areas"""
        # Find booth records
        start = self.find_booth(from_booth)
        end = self.find_booth(to_booth)
        
        if start is None:
            raise ValueError(f"Booth '{from_booth}' not found")
        if end is None:
            raise ValueError(f"Booth '{to_booth}' not found")
        
        # Transform coordinates
        start_x, start_y = self._transform_coordinates(start['x'], start['y'])
        end_x, end_y = self._transform_coordinates(end['x'], end['y'])
        
        path_coords = []
        path_names = [start['booth'], end['booth']]
        
        if self.use_walkable_paths:
            # Use walkable pathfinder
            try:
                path_coords = self.pathfinder.find_path(start_x, start_y, end_x, end_y)
            except Exception as e:
                print(f"Warning: Pathfinding failed, using direct route: {e}")
                path_coords = [(start_x, start_y), (end_x, end_y)]
        else:
            # Direct path
            path_coords = [(start_x, start_y), (end_x, end_y)]
        
        return path_coords, path_names
    
    def draw_route(self, from_booth, to_booth, output_file="route_map.png", show_waypoints=False):
        """Draw the route on the map and return as BytesIO buffer"""
        
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
        
        # Draw waypoints if requested
        if show_waypoints and self.use_walkable_paths:
            # Draw waypoint network in light gray
            for edge in self.pathfinder.nav_graph.edges():
                pos1 = self.pathfinder.nav_graph.nodes[edge[0]]['pos']
                pos2 = self.pathfinder.nav_graph.nodes[edge[1]]['pos']
                draw.line([pos1, pos2], width=1, fill=(200, 200, 200, 100))
        
        # Get start and end positions
        start_x, start_y = path_coords[0]
        end_x, end_y = path_coords[-1]
        
        # Draw large directional arrows instead of lines
        if len(path_coords) > 3:
            # Find the point on the path closest to destination
            min_dist_to_end = float('inf')
            closest_point_idx = 0
            
            for i in range(len(path_coords)):
                dist = ((path_coords[i][0] - end_x)**2 + (path_coords[i][1] - end_y)**2)**0.5
                if dist < min_dist_to_end:
                    min_dist_to_end = dist
                    closest_point_idx = i
            
            # Only use path up to the closest point to destination
            truncated_path = path_coords[:closest_point_idx + 1]
            
            # Build segments for arrow placement
            segments = []
            total_length = 0
            
            for i in range(len(truncated_path) - 1):
                x1, y1 = truncated_path[i]
                x2, y2 = truncated_path[i + 1]
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
            arrow_spacing = 100  # Base spacing between arrows
            arrow_size = 45  # Arrow size
            min_start_distance = 40  # Minimum distance from start for first arrow
            min_end_distance = 100  # Safe distance from destination
            
            # Calculate arrow positions
            arrow_positions = []
            
            if total_length > min_start_distance + min_end_distance:
                # First arrow
                arrow_positions.append(min_start_distance)
                
                # Additional arrows
                current_dist = min_start_distance + arrow_spacing
                
                while current_dist < total_length:
                    # Find position of this potential arrow
                    arrow_x, arrow_y = 0, 0
                    for seg in segments:
                        if seg['start_distance'] <= current_dist < seg['start_distance'] + seg['length']:
                            t = (current_dist - seg['start_distance']) / seg['length']
                            arrow_x = seg['start'][0] + t * (seg['end'][0] - seg['start'][0])
                            arrow_y = seg['start'][1] + t * (seg['end'][1] - seg['start'][1])
                            break
                    
                    # Check distance to destination
                    dist_to_end = ((arrow_x - end_x)**2 + (arrow_y - end_y)**2)**0.5
                    
                    # Stop if too close to destination
                    if dist_to_end < min_end_distance:
                        break
                    
                    arrow_positions.append(current_dist)
                    current_dist += arrow_spacing
            
            # Draw arrows
            for arrow_dist in arrow_positions:
                for seg in segments:
                    if seg['start_distance'] <= arrow_dist < seg['start_distance'] + seg['length']:
                        t = (arrow_dist - seg['start_distance']) / seg['length']
                        arrow_x = seg['start'][0] + t * (seg['end'][0] - seg['start'][0])
                        arrow_y = seg['start'][1] + t * (seg['end'][1] - seg['start'][1])
                        
                        # Draw shadow
                        shadow_offset = 2
                        draw_waze_arrow(draw, arrow_x + shadow_offset, arrow_y + shadow_offset, 
                                    seg['dx_norm'], seg['dy_norm'], arrow_size, 
                                    (0, 0, 0, 30))
                        
                        # Draw arrow
                        draw_waze_arrow(draw, arrow_x, arrow_y, seg['dx_norm'], seg['dy_norm'], arrow_size,
                                    (91, 192, 235, 255))
                        break
        
        elif len(path_coords) > 1:
            # For direct paths, place multiple arrows if the distance is long enough
            dx = end_x - start_x
            dy = end_y - start_y
            length = (dx**2 + dy**2)**0.5
            
            if length > 0:
                # Normalize direction
                dx_norm = dx / length
                dy_norm = dy / length
                
                # Calculate number of arrows based on distance
                arrow_spacing = 120
                min_start_distance = 50
                min_end_distance = 70
                
                if length < 200:  # Short distance - single arrow
                    # Single arrow closer to start
                    t = 0.35  # Place at 35% of the path
                    arrow_x = start_x + t * dx
                    arrow_y = start_y + t * dy
                    arrow_size = 50
                    
                    # Draw shadow
                    shadow_offset = 3
                    draw_waze_arrow(draw, arrow_x + shadow_offset, arrow_y + shadow_offset, 
                                dx_norm, dy_norm, arrow_size, 
                                (0, 0, 0, 40))  # Light shadow
                    
                    # Draw main arrow
                    draw_waze_arrow(draw, arrow_x, arrow_y, dx_norm, dy_norm, arrow_size,
                                (91, 192, 235, 255))  # Light blue like Waze
                else:
                    # Multiple arrows for longer distances
                    arrow_positions = []
                    arrow_size = 45
                    
                    # First arrow near start
                    first_arrow_dist = min_start_distance
                    arrow_positions.append(first_arrow_dist / length)
                    
                    # Additional arrows
                    current_dist = first_arrow_dist + arrow_spacing
                    max_dist = length - min_end_distance
                    
                    while current_dist < max_dist:
                        arrow_positions.append(current_dist / length)
                        current_dist += arrow_spacing
                    
                    # Draw arrows
                    for t in arrow_positions:
                        arrow_x = start_x + t * dx
                        arrow_y = start_y + t * dy
                        
                        # Draw shadow
                        shadow_offset = 2
                        draw_waze_arrow(draw, arrow_x + shadow_offset, arrow_y + shadow_offset, 
                                    dx_norm, dy_norm, arrow_size, 
                                    (0, 0, 0, 30))  # Light shadow
                        
                        # Draw main arrow
                        draw_waze_arrow(draw, arrow_x, arrow_y, dx_norm, dy_norm, arrow_size,
                                    (91, 192, 235, 255))  # Light blue like Waze
        
        # Move markers up to avoid covering booth names
        marker_offset_y = -120  # Move markers up by 120 pixels (reduced from 200px)
        
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
        
        # Draw floating labels with modern style - positioned above the moved markers
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
        
        # Composite the overlay onto the base image
        img = Image.alpha_composite(img, overlay)
        
        # Crop the image to focus on the route area
        # Calculate bounding box with padding
        all_x = [coord[0] for coord in path_coords]
        all_y = [coord[1] for coord in path_coords]
        
        # Include marker positions in bounding box calculation
        all_y.extend([start_y + marker_offset_y - 100, end_y + marker_offset_y - 100])
        
        min_x = max(0, min(all_x) - 200)
        max_x = min(img.width, max(all_x) + 200)
        min_y = max(0, min(all_y) - 100)
        max_y = min(img.height, max(all_y) + 200)
        
        # Ensure minimum size
        width = max_x - min_x
        height = max_y - min_y
        min_dimension = 800
        
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
        
        # Save the result
        img_bytes = io.BytesIO()
        border_img.save(img_bytes, "PNG")
        return img_bytes, path_names
    
    def list_booths(self):
        """List all available booths"""
        return self.booth_data.get_booth_names()


def main():
    """Command line interface"""
    if len(sys.argv) < 3:
        print("Usage: python booth_navigator_walkable.py <from_booth> <to_booth> [options]")
        print("\nOptions:")
        print("  --direct              Use direct path instead of walkable routes")
        print("  --show-waypoints      Show waypoint network on map")
        print("  --output <filename>   Specify output filename")
        print("\nExample: python booth_navigator_walkable.py 'weni by vtex' 'aws' --show-waypoints")
        
        # Show available booths
        navigator = BoothNavigatorWalkable()
        print("\nAvailable booths:")
        booths = navigator.list_booths()
        for i in range(0, len(booths), 4):
            print("  " + "  |  ".join(f"{b:<20}" for b in booths[i:i+4]))
        
        sys.exit(1)
    
    from_booth = sys.argv[1]
    to_booth = sys.argv[2]
    
    # Parse options
    use_walkable = "--direct" not in sys.argv
    show_waypoints = "--show-waypoints" in sys.argv
    
    # Find output filename
    output_file = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    if not output_file:
        output_file = f"route_{from_booth}_to_{to_booth}_walkable.png".replace(" ", "_")
    
    try:
        navigator = BoothNavigatorWalkable(use_walkable_paths=use_walkable)
        img_bytes, path_names = navigator.draw_route(from_booth, to_booth, output_file, 
                                                show_waypoints=show_waypoints)
        
        print(f"✅ Route generated successfully!")
        if use_walkable:
            print(f"📍 Using walkable paths")
        else:
            print(f"📍 Using direct path")
        print(f"🗺️  Map saved to: {Path(output_file).resolve()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 

class WalkablePathfinder:
    def __init__(self, map_image_path="vtex_day_map.png", waypoints_file="custom_waypoints.json"):
        """Initialize the pathfinder with waypoints for walkable areas"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.map_image_path = os.path.join(current_dir, map_image_path)
        
        # Load image dimensions
        if os.path.exists(self.map_image_path):
            with Image.open(self.map_image_path) as img:
                self.img_width, self.img_height = img.size
        else:
            self.img_width, self.img_height = 8000, 5000
        
        # Initialize waypoints for corridors
        # Try to load custom waypoints first
        if os.path.exists(waypoints_file):
            print(f"Loading custom waypoints from {waypoints_file}")
            with open(waypoints_file, 'r') as f:
                self.waypoints = json.load(f)
        else:
            print("Using default waypoints")
            self.waypoints = self._define_waypoints()
        
        # Build navigation graph
        self.nav_graph = self._build_navigation_graph()
        
    def _define_waypoints(self):
        """Define waypoints in corridors and walkable areas"""
        # These waypoints define the main corridors in the venue
        # Based on typical event layout with main corridors between booth areas
        
        waypoints = []
        
        # Main horizontal corridors (estimated from typical venue layout)
        # Top corridor
        for x in range(1000, 7500, 200):
            waypoints.append({'id': f'top_{x}', 'x': x, 'y': 800, 'type': 'corridor'})
        
        # Middle corridors
        for x in range(1000, 7500, 200):
            waypoints.append({'id': f'mid1_{x}', 'x': x, 'y': 1800, 'type': 'corridor'})
            waypoints.append({'id': f'mid2_{x}', 'x': x, 'y': 2800, 'type': 'corridor'})
        
        # Bottom corridor
        for x in range(1000, 7500, 200):
            waypoints.append({'id': f'bot_{x}', 'x': x, 'y': 3800, 'type': 'corridor'})
        
        # Main vertical corridors
        # Left corridors
        for y in range(800, 4000, 200):
            waypoints.append({'id': f'left1_{y}', 'x': 1000, 'y': y, 'type': 'corridor'})
            waypoints.append({'id': f'left2_{y}', 'x': 2000, 'y': y, 'type': 'corridor'})
        
        # Center corridors
        for y in range(800, 4000, 200):
            waypoints.append({'id': f'center1_{y}', 'x': 3500, 'y': y, 'type': 'corridor'})
            waypoints.append({'id': f'center2_{y}', 'x': 4500, 'y': y, 'type': 'corridor'})
        
        # Right corridors
        for y in range(800, 4000, 200):
            waypoints.append({'id': f'right1_{y}', 'x': 6000, 'y': y, 'type': 'corridor'})
            waypoints.append({'id': f'right2_{y}', 'x': 7000, 'y': y, 'type': 'corridor'})
        
        # Add junction points at corridor intersections
        junctions = [
            (1000, 800), (2000, 800), (3500, 800), (4500, 800), (6000, 800), (7000, 800),
            (1000, 1800), (2000, 1800), (3500, 1800), (4500, 1800), (6000, 1800), (7000, 1800),
            (1000, 2800), (2000, 2800), (3500, 2800), (4500, 2800), (6000, 2800), (7000, 2800),
            (1000, 3800), (2000, 3800), (3500, 3800), (4500, 3800), (6000, 3800), (7000, 3800),
        ]
        
        for i, (x, y) in enumerate(junctions):
            waypoints.append({'id': f'junction_{i}', 'x': x, 'y': y, 'type': 'junction'})
        
        return waypoints
    
    def _build_navigation_graph(self):
        """Build a graph connecting nearby waypoints"""
        G = nx.Graph()
        
        # Add all waypoints as nodes
        for wp in self.waypoints:
            G.add_node(wp['id'], pos=(wp['x'], wp['y']), type=wp.get('type', 'corridor'))
        
        # Connect waypoints based on their positions
        # Create a position index for faster lookup
        pos_index = {}
        for wp in self.waypoints:
            key = (wp['x'], wp['y'])
            pos_index[key] = wp['id']
        
        # Connect each waypoint to its neighbors
        for wp in self.waypoints:
            x, y = wp['x'], wp['y']
            
            # Check for horizontal neighbors (same Y, different X)
            for other_wp in self.waypoints:
                if other_wp['id'] == wp['id']:
                    continue
                    
                # Connect if on same horizontal line
                if abs(other_wp['y'] - y) < 10:  # Same Y coordinate (with small tolerance)
                    x_dist = abs(other_wp['x'] - x)
                    # Connect if reasonably close on X axis (up to 600 pixels for corridor segments)
                    if 0 < x_dist <= 600:
                        # Check if there's no closer waypoint in between
                        is_neighbor = True
                        for check_wp in self.waypoints:
                            if check_wp['id'] in [wp['id'], other_wp['id']]:
                                continue
                            # If there's a waypoint between them on the same line, skip
                            if abs(check_wp['y'] - y) < 10:
                                if min(wp['x'], other_wp['x']) < check_wp['x'] < max(wp['x'], other_wp['x']):
                                    is_neighbor = False
                                    break
                        
                        if is_neighbor:
                            G.add_edge(wp['id'], other_wp['id'], weight=x_dist)
                
                # Connect if on same vertical line
                elif abs(other_wp['x'] - x) < 10:  # Same X coordinate (with small tolerance)
                    y_dist = abs(other_wp['y'] - y)
                    # Connect if reasonably close on Y axis (up to 600 pixels for corridor segments)
                    if 0 < y_dist <= 600:
                        # Check if there's no closer waypoint in between
                        is_neighbor = True
                        for check_wp in self.waypoints:
                            if check_wp['id'] in [wp['id'], other_wp['id']]:
                                continue
                            # If there's a waypoint between them on the same line, skip
                            if abs(check_wp['x'] - x) < 10:
                                if min(wp['y'], other_wp['y']) < check_wp['y'] < max(wp['y'], other_wp['y']):
                                    is_neighbor = False
                                    break
                        
                        if is_neighbor:
                            G.add_edge(wp['id'], other_wp['id'], weight=y_dist)
        
        # Ensure graph is connected by checking connectivity
        if not nx.is_connected(G):
            print(f"Warning: Navigation graph is not fully connected. Components: {nx.number_connected_components(G)}")
        
        return G
    
    def find_nearest_waypoint(self, x, y):
        """Find the nearest waypoint to a given position"""
        min_dist = float('inf')
        nearest = None
        
        for wp in self.waypoints:
            dist = sqrt((wp['x'] - x)**2 + (wp['y'] - y)**2)
            if dist < min_dist:
                min_dist = dist
                nearest = wp
        
        return nearest
    
    def find_path(self, start_x, start_y, end_x, end_y):
        """Find a path through walkable areas from start to end"""
        # Find nearest waypoints to start and end
        start_wp = self.find_nearest_waypoint(start_x, start_y)
        end_wp = self.find_nearest_waypoint(end_x, end_y)
        
        if not start_wp or not end_wp:
            # Fallback to direct path
            return [(start_x, start_y), (end_x, end_y)]
        
        # Add temporary nodes for start and end positions
        temp_start = 'temp_start'
        temp_end = 'temp_end'
        
        # Create a copy of the graph and add temporary connections
        G = self.nav_graph.copy()
        G.add_node(temp_start, pos=(start_x, start_y))
        G.add_node(temp_end, pos=(end_x, end_y))
        
        # Connect start/end to nearest waypoints
        start_dist = sqrt((start_x - start_wp['x'])**2 + (start_y - start_wp['y'])**2)
        end_dist = sqrt((end_x - end_wp['x'])**2 + (end_y - end_wp['y'])**2)
        
        G.add_edge(temp_start, start_wp['id'], weight=start_dist)
        G.add_edge(temp_end, end_wp['id'], weight=end_dist)
        
        # Find shortest path
        try:
            path_nodes = nx.shortest_path(G, temp_start, temp_end, weight='weight')
            
            # Convert to coordinates
            path_coords = []
            for node in path_nodes:
                if node in G:
                    pos = G.nodes[node]['pos']
                    path_coords.append(pos)
            
            # Smooth the path
            path_coords = self._smooth_path(path_coords)
            
            return path_coords
            
        except nx.NetworkXNoPath:
            # No path found, return direct line
            return [(start_x, start_y), (end_x, end_y)]
    
    def _smooth_path(self, path_coords):
        """Smooth the path using basic interpolation"""
        if len(path_coords) <= 2:
            return path_coords
        
        # Simple smoothing: add intermediate points on long segments
        smooth_path = [path_coords[0]]
        
        for i in range(1, len(path_coords)):
            prev_x, prev_y = path_coords[i-1]
            curr_x, curr_y = path_coords[i]
            
            dist = sqrt((curr_x - prev_x)**2 + (curr_y - prev_y)**2)
            
            # If segment is long, add intermediate points
            if dist > 400:
                num_intermediate = int(dist / 200)
                for j in range(1, num_intermediate):
                    t = j / num_intermediate
                    inter_x = prev_x + t * (curr_x - prev_x)
                    inter_y = prev_y + t * (curr_y - prev_y)
                    smooth_path.append((inter_x, inter_y))
            
            smooth_path.append((curr_x, curr_y))
        
        return smooth_path
    
    def visualize_waypoints(self, output_file="waypoints_debug.png"):
        """Visualize all waypoints and connections on the map"""
        # Load the base map
        img = Image.open(self.map_image_path).convert("RGBA")
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Draw edges
        for edge in self.nav_graph.edges():
            pos1 = self.nav_graph.nodes[edge[0]]['pos']
            pos2 = self.nav_graph.nodes[edge[1]]['pos']
            draw.line([pos1, pos2], width=2, fill=(0, 0, 255, 100))
        
        # Draw waypoints
        for wp in self.waypoints:
            x, y = wp['x'], wp['y']
            radius = 8 if wp['type'] == 'junction' else 5
            color = (255, 0, 0, 200) if wp['type'] == 'junction' else (0, 255, 0, 200)
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)
        
        # Composite and save
        img = Image.alpha_composite(img, overlay)
        img.save(output_file)
        print(f"Waypoints visualization saved to: {output_file}")
        return output_file


# Load waypoints from file if exists
def load_custom_waypoints(filename="waypoints.json"):
    """Load custom waypoints from a JSON file"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return None


# Save waypoints to file
def save_waypoints(waypoints, filename="waypoints.json"):
    """Save waypoints to a JSON file for editing"""
    with open(filename, 'w') as f:
        json.dump(waypoints, f, indent=2)
    print(f"Waypoints saved to {filename}")


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

        print(f"BOOTH MAP: {from_booth} to {to_booth}")

        try:
            navigator = BoothNavigatorWalkable(use_walkable_paths=True, map_image="vtex_day_map.png")
            img_bytes, path_names = navigator.draw_route(
                    from_booth,
                    to_booth,
                    "route_map.png",  # This is just for reference, not actually saved
                    show_waypoints=False
            )
        
            image_url = self.upload_to_imgur(img_bytes, context)
            
            # Send via WhatsApp
            whatsapp_response = None
            try:
                whatsapp_response = self.send_whatsapp_message(image_url, context)
                whatsapp_status = "Message sent successfully via WhatsApp"
            except Exception as e:
                whatsapp_status = f"WhatsApp delivery failed: {str(e)}"
            
            return TextResponse(data={
                "message": f"Route map from {from_booth} to {to_booth} has been generated successfully",
                "whatsapp_status": whatsapp_status,
                "whatsapp_response": whatsapp_response
            })
        except Exception as e:
            return TextResponse(data={
                "message": "Failed to generate the route map image and send it to the user"
            })