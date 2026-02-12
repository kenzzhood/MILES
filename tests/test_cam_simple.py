import cv2
import time

def test_cam():
    print("Testing Camera... Press 'q' to quit.")
    
    # Try index 0 first, then 1
    for idx in [0, 1]:
        print(f"Opening Camera Index {idx}...")
        cap = cv2.VideoCapture(idx)
        
        if not cap.isOpened():
            print(f"Failed to open Camera {idx}")
            continue
            
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print(f"Camera {idx} opened. Reading frames...")
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame.")
                break
                
            cv2.imshow(f"Test Camera {idx}", frame)
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Frame {frame_count} captured.")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                return

            # Timeout after 10 seconds of testing per camera if user does nothing
            if time.time() - start_time > 10:
                print("10 seconds passed. Switching/Exiting...")
                break
                
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    test_cam()
