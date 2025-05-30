from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import traceback


class SendMapLink(Tool):
    def execute(self, context: Context) -> TextResponse:
        """Send the VTEX Day map PDF link to the user via WhatsApp"""
        map_pdf_url = "https://weni.ai/wp-content/uploads/2025/05/PLANTA-VTEX-DAY-25-12.pdf"
        return TextResponse(data={
            "message": "Mapa do VTEX Day enviado com sucesso! Para traçar uma rota específica, me informe o ponto de partida e o destino.",
            "map_url": map_pdf_url
        })
    # def execute(self, context: Context) -> TextResponse:
    #     """Send the VTEX Day map PDF link to the user via WhatsApp"""
    #     # Get parameters from context
    #     project_uuid = context.project.get("uuid")
    #     urn = context.contact.get("urn")
        
    #     # Get credentials from context
    #     project_token = context.credentials.get("project_token")
        
    #     if not project_uuid or not urn:
    #         return TextResponse(data={
    #             "message": "Não foi possível enviar o mapa. Informações de contato incompletas.",
    #             "error": "Missing required parameters: project_uuid and urn"
    #         })
        
    #     if not project_token:
    #         return TextResponse(data={
    #             "message": "Não foi possível enviar o mapa. Credenciais não configuradas.",
    #             "error": "Missing required credential: project_token"
    #         })
        
    #     # Weni WhatsApp API endpoint
    #     url = "https://flows.weni.ai/api/v2/whatsapp_broadcasts.json"
        
    #     headers = {
    #         "Authorization": f"Token {project_token}",
    #         "Content-Type": "application/json"
    #     }
        
    #     # Map PDF URL
    #     map_pdf_url = "https://weni.ai/wp-content/uploads/2025/05/PLANTA-VTEX-DAY-25-12.pdf"
        
    #     data = {
    #         "urns": [urn],
    #         "project": project_uuid,
    #         "msg": {
    #             "text": "Aqui está o mapa do evento 🗺️",
    #             "attachments": [f"application/pdf:{map_pdf_url}"]
    #         }
    #     }
        
    #     try:
    #         response = requests.post(url, headers=headers, json=data)
    #         response.raise_for_status()
            
    #         return TextResponse(data={
    #             "message": "Mapa do VTEX Day enviado com sucesso! Para traçar uma rota específica, me informe o ponto de partida e o destino.",
    #             "whatsapp_response": response.json(),
    #             "map_url": map_pdf_url
    #         })
            
    #     except requests.exceptions.RequestException as e:
    #         traceback.print_exc()
    #         return TextResponse(data={
    #             "message": "Desculpe, não consegui enviar o mapa no momento. Por favor, tente novamente.",
    #             "error": f"Failed to send WhatsApp message: {str(e)}"
    #         }) 