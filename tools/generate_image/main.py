from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import json


class GenerateImage(Tool):
    def execute(self, context: Context) -> TextResponse:
        generate, status_code = self.generate_image(context)
        if status_code == 201:
            broke = context.parameters.get("broke")[0] # Error proposital
            return TextResponse(data=generate)
        else:
            return TextResponse(data="Failed to generate image")

    def generate_image(self, context: Context):
        
        api_key = context.credentials.get("api_key")
        
        url = "https://flows.weni.ai/api/v2/flow_starts.json"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {api_key}",  # Push API token
        }

        print("headers", headers)
        numero_disparo = context.contact.get("urn")

        data = {
            "flow": "8cb9d2d6-c3be-44bb-960f-df3cdbe18d0a",  # ID do fluxo
            "urns": [f"{numero_disparo}"]           # Número WhatsApp do usuário
        }
        response = requests.post(url, headers=headers, json=data)
         
        if response.status_code == 201:
            return response.json(), response.status_code
        else:
            print(response.json())
            return {"error": f"Failed to trigger stream: {response.status_code}"}


