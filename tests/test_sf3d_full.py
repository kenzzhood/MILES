import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import logging
# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.services.sf3d_service import sf3d_service

def test_integration():
    print("Testing SF3D Integration...")
    
    # 1. Start Service
    print("Starting/Checking Service...")
    if not sf3d_service.start_service():
        print("FAIL: Service did not start.")
        return

    # 2. Prepare Test Image
    # Use the one the user uploaded if possible, or a placeholder.
    # I'll check for a known image in the brain folder or project.
    test_image = r"C:\Users\Goutham Srinath\.gemini\antigravity\brain\62d32a4e-1df1-494b-8e7a-a2c864b208f1\uploaded_image_1765265032784.png"
    if not os.path.exists(test_image):
        print(f"Warning: Test image {test_image} not found. Using dummy check.")
        # If no image, we can't fully test generation.
        # Let's try to find *any* png in the project.
        for root, _, files in os.walk("."):
            for f in files:
                if f.endswith(".png"):
                    test_image = os.path.abspath(os.path.join(root, f))
                    break
            if os.path.exists(test_image): break
    
    print(f"Using test image: {test_image}")
    if not os.path.exists(test_image):
        print("FAIL: No test image found.")
        return

    # 3. Generate
    print("Sending Generation Request (this takes time)...")
    start_time = time.time()
    glb_path = sf3d_service.generate_model(test_image)
    duration = time.time() - start_time
    
    # 4. Validate
    if glb_path and os.path.exists(glb_path):
        print(f"SUCCESS: Model generated at {glb_path}")
        print(f"Time taken: {duration:.2f}s")
    else:
        print("FAIL: Generation returned None or file missing.")

if __name__ == "__main__":
    test_integration()
