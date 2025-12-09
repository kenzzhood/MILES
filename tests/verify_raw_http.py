
import requests
import json
import base64
import os

def test_raw_api_b64():
    BASE_URL = "https://fc44a347167834f737.gradio.live"
    TEST_IMAGE_PATH = r"E:\Projects\MILES\miles_project\Gemini_Generated_Image_twzcqntwzcqntwzc.png"
    
    print(f"Testing Raw API (Base64) at {BASE_URL}...")
    
    # Encode Image
    with open(TEST_IMAGE_PATH, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Gradio Base64 format: "data:image/png;base64,....."
    img_str = f"data:image/png;base64,{b64_data}"
    
    endpoints = ["/api/predict", "/run/predict"]
    
    for ep in endpoints:
        predict_url = BASE_URL + ep
        print(f"Trying {predict_url}...")
        
        payload = {
            "data": [img_str],
            "fn_index": 0 
        }
        
        try:
            r = requests.post(predict_url, json=payload, timeout=30)
            print(f"Status: {r.status_code}")
            if r.status_code == 200:
                print("SUCCESS: 3D Generation Initiated")
                print(r.json())
                return True
            else:
                print(f"Response: {r.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_raw_api_b64()
