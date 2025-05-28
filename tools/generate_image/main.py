from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import json


class GenerateImage(Tool):
    def execute(self, context: Context) -> TextResponse:
        sponsors_data = self.generate_image()
        return TextResponse(data=sponsors_data)

    def generate_image(self):
        url = "https://flows.weni.ai/api/v2/flow_starts.json"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Token c249262414613b7cedfdb2fd99daa8b3964639d5",  # Push API token
        }
        numero_disparo = Context.contact.get("urn")
        
        data = {
            "flow": "8cb9d2d6-c3be-44bb-960f-df3cdbe18d0a",  # ID do fluxo
            "urns": [f"whatsapp:{numero_disparo}"]           # Número WhatsApp do usuário
        }
        
        response = requests.post(url, headers=headers, json=data)
         
        if response.status_code == 201:
            return response.json()
        else:
            return {"error": f"Failed to trigger stream: {response.status_code}"} 
