from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import json


class Getsponsors(Tool):
    def execute(self, context: Context) -> TextResponse:
        sponsors_data = self.get_sponsors()
        return TextResponse(data=sponsors_data)

    def get_sponsors(self):
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
            data = response.json()
            return self.filter_sponsors(data)
        else:
            return {"error": f"Failed to fetch sponsors: {response.status_code}"} 
        
    
    def filter_sponsors(self, data):
        filtered_sponsors = []

        sponsors_list = data[0] if isinstance(data, list) and len(data) > 0 else data

        for sponsor in sponsors_list:
            fields = sponsor.get("fields", {})
            nome = fields.get("nome", {}).get("stringValue", "")
            categoria = fields.get("categoria", {}).get("stringValue", "")
            filtered_sponsors.append({
                "nome": nome,
                "categoria": categoria
            })

        return filtered_sponsors
