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

    def get_plenaria_data(self):
        """Fetch plenaria data to resolve stage names"""
        url = "https://api.coodefy.dev/v1/vtex_plenaria"
        headers = {
            'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7,es;q=0.6,nl;q=0.5,fr;q=0.4',
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InNpdGVfdnRleEB3YXByb2plY3QuY29tLmJyIiwiaWRVc2VyIjoiYXRDN3NDbE9oRGZjdjVGMWRzUnVqRk92cEY1eCIsImlhdCI6MTc0NjYzMzUxOX0.BALB7Lj19rGcoot1sLJhk8F_dKUsEVIp2v-5JjMEQTA',
            'Origin': 'https://vtexday.vtex.com',
            'Referer': 'https://vtexday.vtex.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'accept': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch plenaria data: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error fetching plenaria data: {e}")
            return []

    def process_agenda_data(self, raw_data, context: Context):
        speaker_name = context.parameters.get("speaker")  # Obtem o nome do palestrante
        time_filter = context.parameters.get("time_filter")  # Filtro de tempo (now, current, upcoming, today)
        stage_filter = context.parameters.get("stage")  # Filtro de palco/stage

        if isinstance(raw_data, dict) and "error" in raw_data:
            return raw_data

        # Fetch plenaria data once and create a lookup dictionary
        plenaria_lookup = {}
        plenaria_data = self.get_plenaria_data()
        for plenaria in plenaria_data:
            plenaria_id = plenaria.get("name", "")
            stage_name = plenaria.get("fields", {}).get("name", {}).get("stringValue", "")
            if plenaria_id and stage_name:
                plenaria_lookup[plenaria_id] = stage_name

        formatted_agenda = []
        # TEMPORARY: Setting current time to June 3, 2025 15:00 for testing time filters
        current_time = datetime.now(pytz.timezone('America/Sao_Paulo'))  # Hora atual no fuso horário de Brasília
        # current_time = datetime(2025, 6, 2, 16, 0, 0)  # June 3, 2025 at 15:00
        # current_time = pytz.timezone('America/Sao_Paulo').localize(current_time)
        # print(f"DEBUG: Using simulated current time: {current_time}")

        for event in raw_data:
            if "fields" in event:
                fields = event["fields"]
                speakers_string = fields.get("palestrantes_names", {}).get("stringValue", "")
                
                # Split the speakers string by comma and strip whitespace
                speakers_list = [speaker.strip() for speaker in speakers_string.split(",") if speaker.strip()]

                # Get event timing information
                start_time_str = fields.get("date", {}).get("timestampValue", "")
                end_time_str = fields.get("endDate", {}).get("timestampValue", "")
                
                # Get stage information using the lookup dictionary
                plenaria_reference = fields.get("plenaria", {}).get("referenceValue", "")
                event_stage = plenaria_lookup.get(plenaria_reference, "Unknown Stage")
                
                # Convert times to Brasilia timezone for comparison
                start_time = None
                end_time = None
                if start_time_str:
                    start_time = self.parse_timestamp_to_brasilia(start_time_str)
                if end_time_str:
                    end_time = self.parse_timestamp_to_brasilia(end_time_str)

                # Check if we should include this event based on all filters
                include_event = True

                # Speaker filter
                if speaker_name:
                    speaker_match = False
                    for speaker in speakers_list:
                        if speaker_name.lower() in speaker.lower():
                            speaker_match = True
                            break
                    if not speaker_match:
                        include_event = False

                # Time filter
                if time_filter and include_event:
                    if time_filter.lower() in ['now', 'current']:
                        # Event must be happening right now
                        if not (start_time and end_time and start_time <= current_time <= end_time):
                            include_event = False
                    elif time_filter.lower() == 'upcoming':
                        # Event must start in the future (within next 2 hours)
                        if not (start_time and start_time > current_time and start_time <= current_time.replace(hour=current_time.hour + 2)):
                            include_event = False
                    elif time_filter.lower() == 'today':
                        # Event must be today
                        if not (start_time and start_time.date() == current_time.date()):
                            include_event = False

                # Stage filter - match against resolved stage name
                if stage_filter and include_event:
                    if stage_filter.lower() not in event_stage.lower():
                        include_event = False

                if include_event:
                    # Calculate time status for current events
                    time_status = ""
                    if start_time and end_time:
                        if current_time < start_time:
                            # Future event
                            time_diff = start_time - current_time
                            hours = int(time_diff.total_seconds() // 3600)
                            minutes = int((time_diff.total_seconds() % 3600) // 60)
                            if hours > 0:
                                time_status = f"Starts in {hours}h {minutes}m"
                            else:
                                time_status = f"Starts in {minutes}m"
                        elif start_time <= current_time <= end_time:
                            # Current event
                            time_since_start = current_time - start_time
                            time_until_end = end_time - current_time
                            minutes_since_start = int(time_since_start.total_seconds() // 60)
                            minutes_until_end = int(time_until_end.total_seconds() // 60)
                            time_status = f"Started {minutes_since_start}m ago, ends in {minutes_until_end}m"
                        else:
                            # Past event
                            time_status = "Ended"

                    formatted_event = {
                        "title": fields.get("title", {}).get("stringValue", ""),
                        "description": fields.get("description", {}).get("stringValue", ""),
                        "description_en": fields.get("description_en", {}).get("stringValue", ""),
                        "date": start_time_str,
                        "endDate": end_time_str,
                        "start_time_brasilia": start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else "",
                        "end_time_brasilia": end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else "",
                        "time_status": time_status,
                        "stage": event_stage,
                        "palestrantes_names": speakers_string,
                        "session_url": fields.get("transcricao_palestra", {}).get("stringValue", "")
                    }
                    formatted_agenda.append(formatted_event)

        # Sort by start time for better presentation
        formatted_agenda.sort(key=lambda x: x.get("start_time_brasilia", ""))
        
        return formatted_agenda

    def parse_timestamp_to_brasilia(self, timestamp_str):
        """Parse timestamp and convert to Brasilia timezone"""
        brasilia_tz = pytz.timezone('America/Sao_Paulo')
        try:
            # Try with microseconds
            utc_time = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            # Try without microseconds
            utc_time = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')
        
        utc_time = pytz.utc.localize(utc_time)
        brasilia_time = utc_time.astimezone(brasilia_tz)
        return brasilia_time

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
