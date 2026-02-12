import websocket
import time
import threading

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Closed")

def on_open(ws):
    print("Opened! Sending Hello...")
    ws.send("Hello from Test Script")

if __name__ == "__main__":
    url = "ws://localhost:8001/ws/hologram/tracker"
    print(f"Connecting to {url}...")
    ws = websocket.WebSocketApp(url,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    ws.run_forever()
