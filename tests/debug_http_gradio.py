
import requests
import json

def check_http():
    BASE_URL = "https://fc44a347167834f737.gradio.live"
    
    print(f"Checking {BASE_URL}...")
    
    endpoints = ["/", "/config", "/info"]
    
    for ep in endpoints:
        url = BASE_URL + ep
        try:
            print(f"Fetching {url}...")
            r = requests.get(url, timeout=10)
            print(f"Status: {r.status_code}")
            print(f"Content Type: {r.headers.get('content-type', 'unknown')}")
            if r.status_code == 200 and ep == "/config":
                print("Config Head:", r.text[:200])
        except Exception as e:
            print(f"Error fetching {url}: {e}")

if __name__ == "__main__":
    check_http()
