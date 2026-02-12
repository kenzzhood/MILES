import requests
import sys

# Route is registered at root in main.py, NOT under /api/v1
URL = "http://127.0.0.1:8001/hologram/broadcast"

# Default test model (Apple or whatever exists)
# Ideally we find one in the models dir
import os
def get_latest_model():
    models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    if not os.path.exists(models_dir): return None
    files = [f for f in os.listdir(models_dir) if f.endswith(".glb")]
    if not files: return None
    # Sort by time
    files.sort(key=lambda x: os.path.getmtime(os.path.join(models_dir, x)), reverse=True)
    return files[0]

def trigger():
    model_name = get_latest_model()
    if not model_name:
        print("No .glb models found in 'models/' directory to test with.")
        return

    print(f"Triggering load for: {model_name}")
    try:
        resp = requests.post(URL, json={
            "type": "load_model",
            "data": {"url": f"/models/{model_name}"}
        })
        print(f"Response: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    trigger()
