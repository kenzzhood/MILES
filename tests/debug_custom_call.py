
import base64
import json
import os
import time
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.ai3d.v20250513 import ai3d_client

# Hardcoded config for debugging
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src import config

def debug_custom_call():
    print("Initializing Client...")
    cred = credential.Credential(config.TENCENT_SECRET_ID, config.TENCENT_SECRET_KEY)
    httpProfile = HttpProfile()
    httpProfile.endpoint = "ai3d.tencentcloudapi.com"
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = ai3d_client.Ai3dClient(cred, "ap-guangzhou", clientProfile)

    TEST_IMAGE_PATH = r"E:\Projects\MILES\miles_project\Gemini_Generated_Image_hm1wbkhm1wbkhm1w.png"
    
    if not os.path.exists(TEST_IMAGE_PATH):
        print("Image not found!")
        return

    with open(TEST_IMAGE_PATH, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

    params = {
        "ImageBase64": encoded_string,
        "Prompt": "A futuristic watch"
    }

    print("Attempting manual call to 'SubmitHunyuanTo3DJob'...")
    try:
        response_body = client.call("SubmitHunyuanTo3DJob", params)
        if isinstance(response_body, bytes):
             response_body = response_body.decode('utf-8')
        
        print(f"Raw Response: {response_body}")
        
        response_data = json.loads(response_body)
        if "Response" in response_data and "Error" in response_data["Response"]:
             print(f"API Error: {response_data['Response']['Error']}")
        else:
             print(f"Success! JobId: {response_data['Response']['JobId']}")

    except Exception as e:
        with open("debug_output.txt", "w", encoding="utf-8") as f:
            f.write(f"Exception during call: {e}")
        print(f"Exception logged to debug_output.txt")

if __name__ == "__main__":
    debug_custom_call()
