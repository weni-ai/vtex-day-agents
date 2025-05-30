from weni import Tool
from weni.context import Context
from weni.responses import TextResponse
import requests
import base64
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
            composed_image = self.compose_image(image, background_color)
            
            # Return the response as a dictionary containing the image data
            response_data = {
                "status": "success",
                "image": composed_image,
                "template_used": f"vtex_day_{background_color}"
            }
            return TextResponse(data=response_data)
        except Exception as e:
            return TextResponse(data={
                "status": "error",
                "message": str(e),
                "details": "Failed to generate custom image"
            })

    def compose_image(self, image: str, background_color: str) -> str:
        """
        Call the image composition API to create the VTEX DAY template image
        """
        url = "https://weni.ai/wp-json/composer/v1/compose"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer 47672c7a04fe46abdc2594604ac1f4bf90b6d84793616d327e2a5ec0550046f4"
        }

        if background_color.upper() == "BLUE":
            template = "image/jpeg:https://push-ilha-sp-push-media-prod.s3.sa-east-1.amazonaws.com/media/21385/757c/e900/757ce900-4ea3-4e4c-bf1f-3561fa6a959a.jpg"
        else:
            template = "image/jpeg:https://push-ilha-sp-push-media-prod.s3.sa-east-1.amazonaws.com/media/21385/89f5/541a/89f5541a-3808-4ff5-b5ec-ecfc927f725b.jpg"
        
        payload = {
            "image": image,
            "background_color": background_color,
            "template": template
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to compose image. Status code: {response.status_code}")
            
        return response.json().get("composed_image", "") 