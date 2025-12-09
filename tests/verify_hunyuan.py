import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.workers.tasks_3d_generation import generate_3d_model

def test_hunyuan_generation():
    print("Testing Hunyuan 3D Generation (Direct Call)...")
    
    # This prompt triggers the image-to-3d logic in our worker
    prompt = "Generate a 3D model from the test image of a futuristic watch."
    
    try:
        print(f"Calling worker with prompt: '{prompt}'")
        # Call synchronously for easier debugging of the API
        result = generate_3d_model(prompt)
        
        print(f"\nResult received:")
        print(result)
        
        if "3D Model Generated" in result and ".glb" in result:
            print("\n✅ Hunyuan Verification Passed.")
        else:
            print("\n❌ Verification Failed: Unexpected output.")
            
    except Exception as e:
        print(f"\n❌ Verification Failed with Exception: {e}")

if __name__ == "__main__":
    test_hunyuan_generation()
