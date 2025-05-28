from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import json
import pytz
from datetime import datetime


class GetAgenda(Tool):
    def execute(self, context: Context) -> TextResponse:
        agenda_data = self.get_vtex_day_agenda()
        return TextResponse(data=agenda_data)

    def get_vtex_day_agenda(self):
        url = "https://api.coodefy.dev/v1/vtex_calendar"
        headers = {
            'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6,nl;q=0.5,fr;q=0.4',
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InNpdGVfdnRleEB3YXByb2plY3QuY29tLmJyIiwiaWRVc2VyIjoiYXRDN3NDbE9oRGZjdjVGMWRzUnVqRk92cEY1eCIsImlhdCI6MTc0NjYzMzUxOX0.BALB7Lj19rGcoot1sLJhk8F_dKUsEVIp2v-5JjMEQTA',
            'Origin': 'https://vtexday.vtex.com',
            'Referer': 'https://vtexday.vtex.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        
        # Aplica a conversão para horário de Brasília
        agenda_data = self.process_agenda_data(agenda_data)
        
        if response.status_code == 200:
            print(response.json())
            return response.json()
        else:
            return {"error": f"Failed to fetch agenda: {response.status_code}"}
        
    
    def process_agenda_data(agenda_data):
        for event in agenda_data:
            # Converte o horário de início (date) e o horário de término (endDate)
            if 'date' in event['fields']:
                event['fields']['date_brasilia'] = convert_utc_to_brasilia(event['fields']['date']['timestampValue'])
            
            if 'endDate' in event['fields']:
                event['fields']['endDate_brasilia'] = convert_utc_to_brasilia(event['fields']['endDate']['timestampValue'])
        
        return agenda_data
    
    def convert_utc_to_brasilia(utc_time_str):
        brasilia_tz = pytz.timezone('America/Sao_Paulo')
        
        # Converte a string UTC para datetime
        utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        
        # Atribui o fuso horário UTC
        utc_time = pytz.utc.localize(utc_time)
        
        # Converte para o horário de Brasília
        brasilia_time = utc_time.astimezone(brasilia_tz)
        
        # Retorna o horário no formato desejado
        return brasilia_time.strftime('%Y-%m-%d %H:%M:%S')
    
