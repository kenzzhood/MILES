
import requests

def debug_root():
    URL = "https://fc44a347167834f737.gradio.live"
    print(f"Fetching root of {URL}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        r = requests.get(URL, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        print("--- HEADERS ---")
        print(r.headers)
        print("--- HTML SNIPPET ---")
        print(r.text[:500])
        print("..." + r.text[-500:])
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_root()
