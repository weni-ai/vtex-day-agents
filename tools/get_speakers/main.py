from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import json


class Getspeakers(Tool):
    def execute(self, context: Context) -> TextResponse:
        speakers_data = self.get_vtex_palestrantes()
        formatted_data = self.format_speakers_data(speakers_data, context)
        return TextResponse(data=formatted_data)

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

    def format_speakers_data(self, raw_data, context: Context):
        """Format the speakers data to return only name, description, role, and highlight"""
        if isinstance(raw_data, dict) and "error" in raw_data:
            return raw_data
        
        speaker = context.parameters.get("speaker")
        formatted_speakers = []
        for speaker in raw_data:
            if "fields" in speaker:
                fields = speaker["fields"]
                formatted_speaker = {
                    "name": fields.get("name", {}).get("stringValue", ""),
                    "description": fields.get("description", {}).get("stringValue", ""),
                    "role": fields.get("role", {}).get("stringValue", ""),
                    "highlight": fields.get("highlight", {}).get("booleanValue", False)
                }
                formatted_speakers.append(formatted_speaker)
        
        return formatted_speakers 