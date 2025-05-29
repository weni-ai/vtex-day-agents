from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import json
import pytz
from datetime import datetime

class GetAgenda(Tool):
    def execute(self, context: Context) -> TextResponse:
        agenda_data = self.get_vtex_day_agenda(context)
        return TextResponse(data=agenda_data)

    def get_vtex_day_agenda(self, context: Context):
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

        if response.status_code == 200:
            agenda_data = response.json()  # Pega os dados da resposta
            agenda_data = self.process_agenda_data(agenda_data, context)  # Processa os dados (ex: converter horários)
            return agenda_data
        else:
            return {"error": f"Failed to fetch agenda: {response.status_code}"}

    def process_agenda_data(self, raw_data, context: Context):
        speaker_name = context.parameters.get("speaker")  # Obtem o nome do palestrante

        if isinstance(raw_data, dict) and "error" in raw_data:
            return raw_data

        formatted_agenda = []

        for event in raw_data:
            if "fields" in event:
                fields = event["fields"]
                speakers = fields.get("palestrantes_names", {}).get("stringValue", "")

                # Se o nome do palestrante for vazio ou se o nome do palestrante corresponder ao solicitado, formate o evento
                if not speaker_name or speaker_name in speakers:
                    formatted_event = {
                        "title": fields.get("title", {}).get("stringValue", ""),
                        "description": fields.get("description", {}).get("stringValue", ""),
                        "description_en": fields.get("description_en", {}).get("stringValue", ""),
                        "date": fields.get("date", {}).get("timestampValue", ""),
                        "endDate": fields.get("endDate", {}).get("timestampValue", ""),
                        "palestrantes_names": speakers,
                        "session_url": fields.get("transcricao_palestra", {}).get("stringValue", "")
                    }
                    formatted_agenda.append(formatted_event)

        # Retorna a agenda formatada de acordo com o filtro do palestrante (se fornecido) ou todos os eventos
        return formatted_agenda

    def convert_utc_to_brasilia(self, utc_time_str):
        brasilia_tz = pytz.timezone('America/Sao_Paulo')
        try:
            # Tenta com microssegundos
            utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            # Caso não tenha microssegundos, tenta sem
            utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%SZ')

        utc_time = pytz.utc.localize(utc_time)
        brasilia_time = utc_time.astimezone(brasilia_tz)
        return brasilia_time.strftime('%Y-%m-%d %H:%M:%S')
