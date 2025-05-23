from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import json


class GetPalestrantes(Tool):
    def execute(self, context: Context) -> TextResponse:
        palestrantes_data = self.get_vtex_palestrantes()
        return TextResponse(data=palestrantes_data)

    def get_vtex_palestrantes(self):
        url = "https://api.coodefy.dev/v1/vtex_palestrantes"
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
            return {"error": f"Failed to fetch palestrantes: {response.status_code}"} 