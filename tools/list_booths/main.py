from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import json
import os


class ListBooths(Tool):
    def execute(self, context: Context) -> TextResponse:
        """
        Lists all available locations at VTEX Day including booths, restrooms, stages, 
        food areas, information desks, exits, and entrances with their relative positions (x,y) on a mini-map scale
        """
        
        # Get all locations data
        locations = self.get_all_locations()
        
        # Format the response
        response = self.format_location_list(locations)
        return TextResponse(data=response)
    
    def get_all_locations(self):
        """
        Reads location data from the project.json file.
        """
        locations_data = []
        
        # Get the path to the JSON file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'project.json')
        
        # Define valid categories
        valid_categories = ['booth', 'restroom', 'stage', 'food', 'info', 'exit', 'entrance']
        
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for rect_data in data.get('rectangles', []):
                    item_category = rect_data.get('category', '').lower()
                    
                    # Check if this item matches our valid categories
                    if item_category in valid_categories:
                        location = {
                            "name": rect_data['name'].strip(),
                            "category": self.get_display_category(item_category),
                            "x": (rect_data['x1'] + rect_data['x2']) / 2,  # Center point
                            "y": (rect_data['y1'] + rect_data['y2']) / 2   # Center point
                        }
                        locations_data.append(location)
                        
        except FileNotFoundError:
            # Fallback to some basic locations if JSON not found
            print(f"Warning: project.json not found at {json_path}")
            locations_data = [
                {"name": "VTEX Main Booth", "category": "Booth", "x": 50, "y": 50},
                {"name": "Registration Desk", "category": "Information", "x": 5, "y": 50},
                {"name": "Main Stage", "category": "Stage", "x": 75, "y": 25},
                {"name": "Food Court", "category": "Food", "x": 25, "y": 75}
            ]
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            locations_data = []
        
        return locations_data
    
    def get_display_category(self, category):
        """
        Convert internal category names to user-friendly display names
        """
        display_mapping = {
            'booth': 'Booth',
            'restroom': 'Restroom',
            'stage': 'Stage',
            'food': 'Food',
            'info': 'Information',
            'exit': 'Exit',
            'entrance': 'Entrance'
        }
        return display_mapping.get(category, category.title())
    
    def format_location_list(self, locations):
        """
        Formats the location list for display
        """
        formatted_list = []
        
        # Determine scale based on actual coordinates
        max_x = max([location["x"] for location in locations]) if locations else 100
        max_y = max([location["y"] for location in locations]) if locations else 100
        
        # Group locations by category for better organization
        categories_found = set()
        
        for location in locations:
            location_info = {
                "name": location["name"],
                "category": location["category"],
                "location": {
                    "x": round(location["x"], 2),
                    "y": round(location["y"], 2)
                },
                "description": f"{location['name']} ({location['category']}) located at position ({round(location['x'], 2)}, {round(location['y'], 2)})"
            }
            formatted_list.append(location_info)
            categories_found.add(location["category"])
        
        # Sort locations by category, then by name
        formatted_list.sort(key=lambda x: (x["category"], x["name"]))
        
        response_data = {
            "total_locations": len(formatted_list),
            "locations": formatted_list,
            "categories_found": sorted(list(categories_found)),
            "map_scale": f"{int(max_x)}x{int(max_y)} grid",
            "note": "Coordinates represent relative positions on event floor mini-map"
        }
        
        return response_data