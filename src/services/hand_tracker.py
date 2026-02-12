import cv2
import mediapipe as mp
import math
import sys
import websocket
import time
import threading
import subprocess
import os

# --- CONFIGURATION ---
WIDTH, HEIGHT = 640, 480 
# UPDATED PORT: 8001 matches start_miles.bat
WS_URL = "ws://localhost:8001/ws/hologram/tracker"
HOLOGRAM_URL = "http://localhost:8001/ui/hologram.html"

# --- ADB AUTOMATION ---
def get_adb_path():
    # Check local portable path first
    local_adb = os.path.join(os.path.dirname(__file__), "..", "libs", "adb", "adb.exe")
    if os.path.exists(local_adb):
        return os.path.abspath(local_adb)
    return "adb" # Fallback to global PATH

def setup_adb():
    """
    1. Clear browser cache (preserving login data).
    2. Reverse tether port 8001.
    3. Launch Chrome on Android to the Hologram URL with cache-busting.
    """
    adb_cmd = get_adb_path()
    print(f"[ADB] Using binary: {adb_cmd}")
    print("[ADB] Scanning for Android devices...")
    try:
        # Check devices
        result = subprocess.run([adb_cmd, "devices"], capture_output=True, text=True)
        if "device" not in result.stdout.replace("List of devices attached", "").strip():
            print("[ADB] No device found. Make sure USB Debugging is ON.")
            return

        print("[ADB] Device detected. Clearing browser cache (preserving logins)...")
        # Force-stop Chrome to release cache locks
        subprocess.run([adb_cmd, "shell", "am", "force-stop", "com.android.chrome"], 
                      capture_output=True)
        
        # Delete only cache directory (preserves cookies/login data)
        print("[ADB] Removing cached files only...")
        subprocess.run([adb_cmd, "shell", "rm", "-rf", "/data/data/com.android.chrome/cache/*"], 
                      capture_output=True)
        
        print("[ADB] Setting up reverse tether...")
        # Reverse port 8001 so phone can access laptop localhost:8001
        subprocess.run([adb_cmd, "reverse", "tcp:8001", "tcp:8001"])

        # Add timestamp to URL to force cache bypass
        import time
        cache_buster = int(time.time())
        url_with_cache_buster = f"{HOLOGRAM_URL}?v={cache_buster}"
        
        print(f"[ADB] Launching Browser with cache-buster: v={cache_buster}...")
        # Force open default browser via Intent
        subprocess.run([
            adb_cmd, "shell", "am", "start", 
            "-a", "android.intent.action.VIEW", 
            "-d", url_with_cache_buster
        ])
        print("[ADB] Launch successful! Cache bypassed.")
        
    except FileNotFoundError:
        print("[ADB] Warning: 'adb' command not found. Install Android Platform Tools.")
    except Exception as e:
        print(f"[ADB] Error: {e}")

# ... (rest of imports) ...

# --- MEDIAPIPE SETUP ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# --- WEBSOCKET CLIENT ---
ws = None

def on_message(ws, message):
    print(f"Server: {message}")

def on_error(ws, error):
    print(f"WS Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WS Connection closed")

def on_open(ws):
    print("WS Connection opened")

def connect_ws():
    global ws
    def run_ws():
        global ws  # CRITICAL: Must declare global here too!
        while True:
            try:
                print(f"[WS] Connecting to {WS_URL}...")
                ws = websocket.WebSocketApp(WS_URL,
                                        on_open=on_open,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_close=on_close)
                ws.run_forever()
                print("[WS] Reconnecting in 3s...")
                time.sleep(3)
            except Exception as e:
                print(f"[WS] Connection failed: {e}")
                time.sleep(3)

    wst = threading.Thread(target=run_ws)
    wst.daemon = True
    wst.start()

# --- HELPER FUNCTIONS ---

def find_available_cameras():
    available = []
    for i in range(3): 
        cap = cv2.VideoCapture(i)
        if cap is not None and cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append(i)
            cap.release()
    return available

def initialize_camera(camera_index):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    return cap

def vector_distance(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

def detect_gestures(hand_landmarks):
    thumb = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    index = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

    pinch_position = {'x': (thumb.x + index.x) / 2, 'y': (thumb.y + index.y) / 2, 'z': (thumb.z + index.z) / 2}
    grab_position = {'x': wrist.x, 'y': wrist.y, 'z': wrist.z}

    return {
        'pinch': {'active': vector_distance(thumb, index) < 0.06, 'position': pinch_position},
        'grab': {'active': (vector_distance(thumb, middle) < 0.07 and 
                           vector_distance(thumb, ring) < 0.07 and
                           vector_distance(thumb, pinky) < 0.07), 'position': grab_position},
        'index_point': (vector_distance(index, wrist) > 0.2 and 
                          vector_distance(index, middle) > 0.2 and 
                          vector_distance(index, thumb) > 0.1),
    }

def main():
    print("Initializing Hand Tracker...")
    
    # 0. Setup ADB Display
    setup_adb()
    
    # 1. Start WS
    connect_ws()
    
    # 2. Camera
    cameras = find_available_cameras()
    if not cameras:
        print("No cameras found.")
        sys.exit(1)
        
    camera_idx = cameras[0] # Default to 0, user can change if needed
    print(f"Using camera {camera_idx}")
    
    cap = initialize_camera(camera_idx)
    
    print("Running... Press 'q' to quit.")
    
    failure_count = 0
    camera_list = cameras
    current_cam_idx_ptr = 0
    
    cv2.namedWindow("Hand Tracker", cv2.WINDOW_NORMAL)

    try:
        while True:
            # Camera Read
            success, img = cap.read()
            if not success:
                # ... existing failure logic ...
                failure_count += 1
                if failure_count % 50 == 0:
                    print(f"[CAM] Warning: Camera {camera_list[current_cam_idx_ptr]} not sending frames. (Fail: {failure_count})")
                if failure_count > 150:
                    print("[CAM] Attempting to switch camera...")
                    cap.release()
                    current_cam_idx_ptr = (current_cam_idx_ptr + 1) % len(camera_list)
                    next_cam = camera_list[current_cam_idx_ptr]
                    # ...
                    cap = initialize_camera(next_cam)
                    failure_count = 0
                    time.sleep(1)
                continue
            
            # SUCCESS CASE
            # Reset counter on success
            if failure_count > 0:
                print("[CAM] Frame received! Camera is working.")
                failure_count = 0

            img = cv2.flip(img, 1)

            # Check for black frames (common driver issue)
            if img.mean() < 5:
                print("[CAM] Warning: Frame is pitch black (Mean < 5). Check lighting or lens cover.")
            
            # --- PROFLLING (Optional) ---
            # print("DEBUG: Processing MediaPipe...")
            results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            # print("DEBUG: MediaPipe Done")
            
            data = [0, 0, 0, 0, 0, 0, 0, 0, 0] 

            if results.multi_hand_landmarks:
                print(f"[HAND] Detected! Landmarks found. Sending to WS...")
                hand = results.multi_hand_landmarks[0]
                gestures = detect_gestures(hand)
                # ... mapping ...
                data = [
                    int(gestures['pinch']['active']),
                    gestures['pinch']['position']['x'],
                    gestures['pinch']['position']['y'],
                    gestures['pinch']['position']['z'],
                    int(gestures['grab']['active']),
                    gestures['grab']['position']['x'],
                    gestures['grab']['position']['y'],
                    gestures['grab']['position']['z'],
                    int(gestures['index_point'])
                ]
                # Overlay
                cv2.putText(img, f"Grab: {data[4]} X:{data[5]:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Send data directly, handle errors if disconnected
            if ws:
                try:
                    msg = ','.join(map(str, data))
                    print(f"DEBUG: Sending WS... {msg[:10]}")
                    ws.send(msg)
                    # print("DEBUG: WS Sent")
                except Exception as e:
                    print(f"DEBUG: Send failed: {e}")
            else:
                pass

            cv2.imshow("Hand Tracker", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if ws:
            ws.close()

if __name__ == "__main__":
    main()
