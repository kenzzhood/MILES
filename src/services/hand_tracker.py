"""
MILES Hand Tracker — Production
Implements the exact HoloInteract spec:
  - MediaPipe Hands (model_complexity=0 for speed)
  - Adaptive pinch threshold (scales with hand proximity)
  - Crowd filter (wrist→middle_mcp distance guard)
  - Gesture debounce (2 frames)
  - Projection mapping support (mapping_config.json)
  - UDP to 127.0.0.1:5052
  - Opens hologram viewer in browser on startup
"""

import cv2
import mediapipe as mp
import socket
import math
import sys
import time
import numpy as np
import json
import os
import webbrowser

# ── CONFIGURATION ────────────────────────────────────────────────────────────
width, height = 640, 480
host, port    = "127.0.0.1", 5052

SHOW_PREVIEW        = False
HUD_WIDTH           = 300
HUD_HEIGHT          = 80
MAPPING_CONFIG_PATH = "mapping_config.json"
MIN_HAND_SIZE_THRESHOLD  = 0.18
GESTURE_DEBOUNCE_FRAMES  = 2

HOLOGRAM_URL = "http://localhost:8001/ui/hologram.html"

# ── MEDIAPIPE SETUP ───────────────────────────────────────────────────────────
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.6,
)

# ── SOCKET SETUP ──────────────────────────────────────────────────────────────
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ── PROJECTION MAPPING ────────────────────────────────────────────────────────
projection_transform = None

def load_projection_config():
    global projection_transform
    if not os.path.exists(MAPPING_CONFIG_PATH):
        projection_transform = None
        return
    try:
        with open(MAPPING_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        surfaces = config.get('surfaces', [])
        if not surfaces:
            projection_transform = None
            return
        main_surface = next(
            (s for s in surfaces if s.get('id') == 'main-view'), surfaces[0]
        )
        corners = main_surface.get('corners', [])
        if len(corners) != 4:
            projection_transform = None
            return
        screen_w, screen_h = 1920, 1080
        src_pts = np.float32([
            [corners[0]['x'] * screen_w, corners[0]['y'] * screen_h],
            [corners[1]['x'] * screen_w, corners[1]['y'] * screen_h],
            [corners[2]['x'] * screen_w, corners[2]['y'] * screen_h],
            [corners[3]['x'] * screen_w, corners[3]['y'] * screen_h],
        ])
        dst_pts = np.float32([
            [0, 0], [screen_w, 0], [screen_w, screen_h], [0, screen_h]
        ])
        projection_transform = cv2.getPerspectiveTransform(src_pts, dst_pts)
        print(f"✓ Projection mapping loaded: {main_surface.get('id')}")
    except Exception as e:
        print(f"Error loading projection config: {e}")
        projection_transform = None

def remap_coordinates(x, y):
    if projection_transform is None:
        return x, y
    screen_w, screen_h = 1920, 1080
    point = np.array([[[x * screen_w, y * screen_h]]], dtype=np.float32)
    transformed = cv2.perspectiveTransform(point, projection_transform)
    new_x = max(0.0, min(1.0, transformed[0][0][0] / screen_w))
    new_y = max(0.0, min(1.0, transformed[0][0][1] / screen_h))
    return new_x, new_y

# ── CAMERA HELPERS ────────────────────────────────────────────────────────────
def find_available_cameras():
    available = []
    for i in range(5):
        try:
            cap = cv2.VideoCapture(i)
            if cap is not None and cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(i)
                cap.release()
        except Exception:
            pass
    return available

def initialize_camera(camera_index):
    try:
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)  # low-latency on Windows
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return None
        ret, _ = cap.read()
        if not ret:
            cap.release()
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS,          30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)   # no frame lag
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        return cap
    except Exception as e:
        print(f"Camera init error: {e}")
        return None

def switch_camera(new_index, current_cap):
    if current_cap is not None:
        current_cap.release()
        time.sleep(0.15)
    return initialize_camera(new_index)

# ── GESTURE HELPERS ───────────────────────────────────────────────────────────
def vector_distance(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)

def distance_2d(a, b):
    return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)

def detect_gestures(hand_landmarks, hand_size):
    """Exact spec gesture detection: adaptive pinch threshold, crowd filter."""
    thumb  = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    index  = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    middle = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    ring   = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    pinky  = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    wrist  = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]

    # Adaptive pinch threshold — scales with hand proximity
    pinch_threshold = max(0.05, min(0.12, 0.06 * (hand_size / 0.2)))
    pinch_distance  = vector_distance(thumb, index)
    is_pinching     = pinch_distance < pinch_threshold

    # Open hand: spread fingers
    spread_threshold  = 0.06 * (hand_size / 0.2)
    fingers_extended  = (
        pinch_distance > spread_threshold and
        vector_distance(index, middle) > 0.02 and
        vector_distance(middle, ring)  > 0.01 and
        vector_distance(ring,   pinky) > 0.01
    )

    return {
        'pinch': {
            'active': is_pinching,
            'position': {
                'x': (thumb.x + index.x) / 2,
                'y': (thumb.y + index.y) / 2,
                'z': (thumb.z + index.z) / 2,
            }
        },
        'open_hand': {
            'active':    fingers_extended,
            'hand_size': distance_2d(wrist, middle),
            'position':  {'x': wrist.x, 'y': wrist.y, 'z': wrist.z},
        }
    }

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("MILES HAND TRACKER — PRODUCTION MODE")
    print("=" * 50)

    load_projection_config()

    available_cameras = find_available_cameras()
    if not available_cameras:
        print("FATAL: No cameras detected!")
        sys.exit(1)

    print(f"Available cameras: {available_cameras}")

    # Prefer camera 1 (external webcam), else highest index
    camera_to_use = 1 if 1 in available_cameras else max(available_cameras)
    print(f"✓ Using Camera {camera_to_use}")

    cap = initialize_camera(camera_to_use)
    if cap is None:
        print(f"FATAL: Could not open camera {camera_to_use}")
        sys.exit(1)

    print(f"Camera {camera_to_use} initialized at {width}x{height}")

    # ── Open hologram in browser ──────────────────────────────────────────
    import time as _t
    _t.sleep(1.0)  # Give the server a moment
    print(f"[BROWSER] Opening display at: {HOLOGRAM_URL}")
    webbrowser.open(HOLOGRAM_URL)
    print("[BROWSER] ✓ Browser tab launched.")

    print("System ready. Waiting for interactions...")
    print("  - PINCH = Rotate (×8.0 Y, ×6.0 X)")
    print("  - OPEN HAND = Zoom (×15.0)")
    print("\nCAMERA CONTROLS (focus the HUD window):")
    print("  - Q = Next camera  |  0–4 = Specific camera  |  ESC = Quit")

    # ── HUD window ───────────────────────────────────────────────────────
    hud_canvas = np.zeros((HUD_HEIGHT, HUD_WIDTH, 3), dtype=np.uint8)
    cv2.namedWindow('HoloInteract | Q=Next Cam  ESC=Quit', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('HoloInteract | Q=Next Cam  ESC=Quit', HUD_WIDTH, HUD_HEIGHT)
    cv2.imshow('HoloInteract | Q=Next Cam  ESC=Quit', hud_canvas)

    # ── State ─────────────────────────────────────────────────────────────
    pinch_frames       = 0
    open_frames        = 0
    no_hand_frames     = 0
    consecutive_errors = 0
    MAX_ERRORS         = 10
    last_valid_data    = [0, 0.5, 0.5, 0, 0, 0.2, 0.5, 0.5]
    current_camera_idx = available_cameras.index(camera_to_use)
    switching_camera   = False

    while True:
        try:
            success, img = cap.read()
            if not success:
                consecutive_errors += 1
                if consecutive_errors > MAX_ERRORS:
                    print("Reinitializing camera...")
                    cap.release()
                    time.sleep(1)
                    cap = initialize_camera(camera_to_use)
                    if cap is None:
                        print("FATAL: Camera lost. Exiting.")
                        break
                    consecutive_errors = 0
                continue

            consecutive_errors = 0
            img = cv2.flip(img, 1)  # mirror
            results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

            data         = [0, 0.5, 0.5, 0, 0, 0.2, 0.5, 0.5]
            hand_detected = False

            if results.multi_hand_landmarks:
                hand           = results.multi_hand_landmarks[0]
                wrist_lm       = hand.landmark[mp_hands.HandLandmark.WRIST]
                middle_mcp_lm  = hand.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]

                # ── Crowd filter: only process close-enough hands ─────────
                hand_check_size = math.sqrt(
                    (wrist_lm.x - middle_mcp_lm.x)**2 +
                    (wrist_lm.y - middle_mcp_lm.y)**2
                )

                if hand_check_size > MIN_HAND_SIZE_THRESHOLD:
                    hand_detected  = True
                    no_hand_frames = 0
                    gestures       = detect_gestures(hand, hand_check_size)

                    # Apply projection remapping to coordinates
                    pinch_x, pinch_y = remap_coordinates(
                        gestures['pinch']['position']['x'],
                        gestures['pinch']['position']['y'],
                    )
                    wrist_x, wrist_y = remap_coordinates(
                        gestures['open_hand']['position']['x'],
                        gestures['open_hand']['position']['y'],
                    )

                    # ── Debounce counters (spec: 2 frames, decay by 1 when inactive) ──
                    if gestures['pinch']['active']:
                        pinch_frames += 1
                        open_frames   = 0
                    elif gestures['open_hand']['active']:
                        open_frames  += 1
                        pinch_frames  = 0
                    else:
                        pinch_frames = max(0, pinch_frames - 1)
                        open_frames  = max(0, open_frames  - 1)

                    data = [
                        1 if pinch_frames >= GESTURE_DEBOUNCE_FRAMES else 0,
                        pinch_x,
                        pinch_y,
                        gestures['pinch']['position']['z'],
                        1 if open_frames >= GESTURE_DEBOUNCE_FRAMES else 0,
                        gestures['open_hand']['hand_size'],
                        wrist_x,
                        wrist_y,
                    ]
                    last_valid_data = data

            if not hand_detected:
                no_hand_frames += 1
                # Fast decay when no hand (spec: decay by 2)
                pinch_frames = max(0, pinch_frames - 2)
                open_frames  = max(0, open_frames  - 2)

                if no_hand_frames > 30:
                    # After ~1s with no hand → send idle packet
                    data = [0, 0.5, 0.5, 0, 0, 0.2, 0.5, 0.5]
                else:
                    # Keep last valid coords, update gesture flags with decayed counters
                    data    = last_valid_data.copy()
                    data[0] = 1 if pinch_frames >= GESTURE_DEBOUNCE_FRAMES else 0
                    data[4] = 1 if open_frames  >= GESTURE_DEBOUNCE_FRAMES else 0

            # ── Send UDP packet ───────────────────────────────────────────
            sock.sendto(
                ','.join(map(str, data)).encode(),
                (host, port)
            )

            # ── HUD update ────────────────────────────────────────────────
            hud_canvas[:] = (20, 20, 20)
            cameras_str = '  '.join(
                [f'[{c}]' if c == camera_to_use else str(c) for c in available_cameras]
            )
            hand_color = (0, 220, 80) if hand_detected else (60, 60, 60)
            cv2.putText(hud_canvas, f"Cam: {cameras_str}", (8, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
            cv2.putText(hud_canvas, "HAND" if hand_detected else "---", (8, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, hand_color, 1, cv2.LINE_AA)
            cv2.putText(hud_canvas, "Q=Next Cam  ESC=Quit", (8, 72),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (100, 100, 100), 1, cv2.LINE_AA)
            cv2.imshow('HoloInteract | Q=Next Cam  ESC=Quit', hud_canvas)

            # ── Key handling ──────────────────────────────────────────────
            key = cv2.waitKey(1) & 0xFF

            if key == 27:  # ESC
                break

            elif (key in (ord('q'), ord('Q'))) and not switching_camera:
                switching_camera   = True
                current_camera_idx = (current_camera_idx + 1) % len(available_cameras)
                camera_to_use      = available_cameras[current_camera_idx]
                print(f"\n🔄 Switching to camera {camera_to_use}...")
                cap = switch_camera(camera_to_use, cap)
                if cap is None:
                    cap = initialize_camera(camera_to_use)
                print(f"✓ Now using camera {camera_to_use}")
                switching_camera = False

            elif key in (ord('0'), ord('1'), ord('2'), ord('3'), ord('4')) and not switching_camera:
                requested = key - ord('0')
                if requested in available_cameras:
                    switching_camera   = True
                    cap                = switch_camera(requested, cap)
                    camera_to_use      = requested
                    current_camera_idx = available_cameras.index(requested)
                    if cap is None:
                        cap = initialize_camera(camera_to_use)
                    switching_camera = False

        except Exception as e:
            print(f"Runtime error: {e}")
            consecutive_errors += 1
            if consecutive_errors > MAX_ERRORS:
                time.sleep(2)
                consecutive_errors = 0

    cap.release()
    cv2.destroyAllWindows()
    sock.close()


if __name__ == "__main__":
    main()
