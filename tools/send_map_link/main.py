from weni import Tool
from weni.context import Context
from weni.responses import TextResponse


class SendMapLink(Tool):
    def execute(self, context: Context) -> TextResponse:
        """Send the VTEX Day map PDF link to the user via WhatsApp"""
        map_pdf_url = "https://weni.ai/wp-content/uploads/2025/05/PLANTA-VTEX-DAY-25-12.pdf"
        return TextResponse(data={
            "map_url": map_pdf_url
        })