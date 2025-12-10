"""
Verification Script for Concept-to-3D Pipeline
"""
import sys
import os
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.memory import memory
from src.services.image_gen_service import image_gen_service
from src.workers.tasks_3d_generation import generate_3d_model

def test_pipeline():
    print("=== Testing Concept-to-3D Pipeline ===")
    
    # 1. Test Image Gen
    prompt = "a retro red telephone"
    print(f"1. Generating Image for: '{prompt}'")
    try:
        image_path = image_gen_service.generate_image(prompt)
        print(f"2. Image generated at: {image_path}")
    except Exception as e:
        print(f"FAIL: Image Generation error: {e}")
        return

    # 3. Test Memory Registration (Automatic in generate_image)
    print(f"3. Checking Memory for active file...")
    if image_path in memory.active_session_files:
        print("PASS: File registered in memory.")
    else:
        print("FAIL: File not in memory.")

    # 4. Test 3D Generation (Mock or Real)
    # Since SF3D might be slow/heavy, we can just test if the worker accepts the path
    # But ideally we run it. Let's try running it.
    print("4. Starting 3D Generation (this might take time)...")
    try:
        # We call the worker directly (ignoring Celery async for this test)
        result = generate_3d_model(image_path)
        print(f"5. Result: {result}")
    except Exception as e:
        print(f"FAIL: 3D Generation error: {e}")
        return

    # 6. Test Save
    print("6. Testing Save Functionality...")
    # Assume the result contains the filename or we can check the last file in memory
    # The worker registers the GLB in memory too.
    
    # Identify the GLB
    glb_path = None
    for f in memory.active_session_files:
        if f.endswith(".glb"):
            glb_path = f
    
    if glb_path:
        print(f"Found GLB in memory: {glb_path}")
        saved_path = memory.save_model_permanently(os.path.basename(glb_path))
        if os.path.exists(saved_path):
             print(f"PASS: Model saved to {saved_path}")
        else:
             print("FAIL: Saved file not found.")
    else:
        print("WARNING: No GLB found in memory (did generation fail?). Skipping save test.")

if __name__ == "__main__":
    test_pipeline()
