from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import base64
import json
from io import BytesIO


class CustomImage(Tool):
    def execute(self, context: Context) -> TextResponse:
        # Get parameters from context
        image = context.parameters.get("image", "")  # Base64 image
        background_color = context.parameters.get("background_color", "pink")  # pink or blue

        if not image:
            return TextResponse(data="Please provide an image.")

        if background_color not in ["pink", "blue"]:
            return TextResponse(data="Please choose either 'pink' or 'blue' as the background color.")

        try:
            # Call the image composition API
            composed_image = self.compose_image(image, background_color, context)
            print("Composed Image URL:", composed_image)  # Debug print
            
            # Send via WhatsApp
            whatsapp_response = None
            whatsapp_status = None
            try:
                whatsapp_response = self.send_whatsapp_message(composed_image, context)
                whatsapp_status = "Message sent successfully via WhatsApp"
            except Exception as e:
                whatsapp_status = f"WhatsApp delivery failed: {str(e)}"
            
            # Return the response as a dictionary containing the image data
            response_data = {
                "status": "success",
                "image": composed_image,
                "template_used": f"vtex_day_{background_color}",
                "whatsapp_status": whatsapp_status,
                "whatsapp_response": whatsapp_response
            }
            return TextResponse(data=response_data)
        except Exception as e:
            return TextResponse(data={
                "status": "error",
                "message": str(e),
                "details": "Failed to generate custom image"
            })

    def compose_image(self, image: str, background_color: str, context: Context) -> str:
        """
        Call the image composition API to create the VTEX DAY template image
        """
        url = "https://weni.ai/wp-json/composer/v1/compose"
        
        api_image_key = context.credentials.get("api_image_key", "")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_image_key}"
        }
        

        payload = {
            "image_url": image,
            "template": background_color,
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            print("Error: ", response.status_code)
            print("Response: ", response.json())
            raise Exception(f"Failed to compose image. Status code: {response.status_code}")
        
        composed_url = response.json().get("image_url", "")
        print("API Response URL:", composed_url)  # Debug print
            
        return composed_url

    def send_whatsapp_message(self, image_url: str, context: Context) -> dict:
        """Send the composed image to the user via WhatsApp"""
        print("Received Image URL in WhatsApp function:", image_url)  # Debug print
        
        # Get parameters from context
        project_uuid = context.project.get("uuid")
        urn = context.contact.get("urn")
        #urn = "whatsapp:5585999854658"
        #project_uuid = "1deff1d8-d263-49ff-a685-41f5caeb12de"
        
        # Get credentials from context
        project_token = context.credentials.get("project_token")
        
        if not project_uuid or not urn:
            raise Exception("Missing required parameters: project_uuid and urn")
        
        if not project_token:
            raise Exception("Missing required credential: project_token")
        
        # Weni WhatsApp API endpoint
        url = "https://flows.weni.ai/api/v2/whatsapp_broadcasts.json"
        
        headers = {
            "Authorization": f"Token {project_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "urns": [urn],
            "project": project_uuid,
            "msg": {
                "text": "Aqui está sua foto personalizada do VTEX Day! 🎉",
                "attachments": [f"image/png:{image_url}"]
            }
        }
        
        print("WhatsApp Request Data:", json.dumps(data, indent=4))  # Debug print
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to send WhatsApp message: {str(e)}") 