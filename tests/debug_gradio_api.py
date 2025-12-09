
from gradio_client import Client

def inspect_api():
    # URL provided by user
    COLAB_URL = "https://fc44a347167834f737.gradio.live"
    
    print(f"Connecting to {COLAB_URL}...")
    try:
        client = Client(COLAB_URL)
        print("Connected!")
        print("-" * 20)
        print("Available Endpoints:")
        client.view_api()
        print("-" * 20)
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    inspect_api()
