from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import json


class Getsponsors(Tool):
    def execute(self, context: Context) -> TextResponse:
        sponsors_data = self.get_vtex_patrocinadores()
        return TextResponse(data=sponsors_data)

    def get_vtex_patrocinadores(self):
        url = "https://api.coodefy.dev/v1/vtex_patrocinadores"
        headers = {
            'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
            'Origin': 'https://vtexday.vtex.com',
            'Referer': 'https://vtexday.vtex.com/',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'accept': '*/*'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to fetch patrocinadores: {response.status_code}"} 
