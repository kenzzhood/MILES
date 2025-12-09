
import sys
import os
import time

def test_bridge():
    print("Testing Colab Bridge (Standalone)...")
    
    # HARDCODED CONFIG (Must match tasks_3d_generation.py)
    COLAB_URL = "https://fc44a347167834f737.gradio.live"
    TEST_IMAGE_PATH = r"E:\Projects\MILES\miles_project\Gemini_Generated_Image_twzcqntwzcqntwzc.png"
    
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"Error: Image not found at {TEST_IMAGE_PATH}")
        return False
        
    try:
        from gradio_client import Client
        
        print(f"Connecting to Colab Bridge at {COLAB_URL}...")
        client = Client(COLAB_URL)
        
        print(f"Sending image: {TEST_IMAGE_PATH}")
        # The API expects an image input. Gradio Client handles file upload.
        result = client.predict(
            TEST_IMAGE_PATH,
            api_name="/predict" 
        )
        
        # Result is typically a path to the downloaded file
        print(f"SUCCESS: Received result from Colab: {result}")
        return True

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return False

if __name__ == "__main__":
    test_bridge()
