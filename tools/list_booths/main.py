from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import json
import os


class ListBooths(Tool):
    def execute(self, context: Context) -> TextResponse:
        """
        Lists all available booths at VTEX Day with company names 
        and their relative positions (x,y) on a mini-map scale
        """
        
        # Get all booths data
        booths = self.get_all_booths()
        
        # Format the response
        response = self.format_booth_list(booths)
        return TextResponse(data=response)
    
    def get_all_booths(self):
        """
        Reads booth data from the project.json file.
        """
        booths_data = []
        
        # Get the path to the JSON file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'project.json')
        
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for rect_data in data.get('rectangles', []):
                    if rect_data.get('category') == 'booth':
                        booth = {
                            "name": rect_data['name'].strip(),
                            "company": rect_data['name'].strip(),  # Using booth name as company name
                            "x": (rect_data['x1'] + rect_data['x2']) / 2,  # Center point
                            "y": (rect_data['y1'] + rect_data['y2']) / 2   # Center point
                        }
                        booths_data.append(booth)
        except FileNotFoundError:
            # Fallback to some basic booths if JSON not found
            print(f"Warning: project.json not found at {json_path}")
            booths_data = [
                {"name": "VTEX Main Booth", "company": "VTEX", "x": 50, "y": 50},
                {"name": "Registration Desk", "company": "Event Staff", "x": 5, "y": 50}
            ]
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            booths_data = []
        
        return booths_data
    
    def format_booth_list(self, booths):
        """
        Formats the booth list for display
        """
        formatted_list = []
        
        # Determine scale based on actual coordinates
        max_x = max([booth["x"] for booth in booths]) if booths else 100
        max_y = max([booth["y"] for booth in booths]) if booths else 100
        
        for booth in booths:
            booth_info = {
                "company": booth["company"],
                "location": {
                    "x": round(booth["x"], 2),
                    "y": round(booth["y"], 2)
                },
                "description": f"{booth['company']} booth located at position ({round(booth['x'], 2)}, {round(booth['y'], 2)})"
            }
            formatted_list.append(booth_info)
        
        return {
            "total_booths": len(formatted_list),
            "booths": formatted_list,
            "map_scale": f"{int(max_x)}x{int(max_y)} grid",
            "note": "Coordinates represent relative positions on event floor mini-map"
        } 