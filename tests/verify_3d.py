import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.workers.tasks_3d_generation import generate_3d_model

def test_3d_generation():
    print("Testing 3D Generation Task (Async via Celery)...")
    prompt = "A futuristic silver watch with a holographic display"
    
    try:
        print(f"Sending task for prompt: '{prompt}'")
        # Call the task asynchronously using Celery
        async_result = generate_3d_model.delay(prompt)
        print(f"Task ID: {async_result.id}")
        print("Waiting for result (this simulates a 30s process)...")
        
        # Wait for the result
        result = async_result.get(timeout=60)
        
        print(f"\nResult received:")
        print(result)
        
        if "3D model for" in result and ".glb" in result:
            print("\n✅ 3D Generation Verification Passed.")
        else:
            print("\n❌ Verification Failed: Unexpected output format.")
            
    except Exception as e:
        print(f"\n❌ 3D Generation Verification Failed: {e}")
        print("Ensure Redis is running and the Celery worker is started.")

if __name__ == "__main__":
    test_3d_generation()
