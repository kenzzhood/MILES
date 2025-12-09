import sys
import os
import traceback
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.workers.tasks_3d_generation import generate_3d_model

def debug_hunyuan():
    print("Debugging Hunyuan 3D Generation...")
    prompt = "Generate a 3D model from the test image of a futuristic watch."
    
    try:
        result = generate_3d_model(prompt)
        print(f"Result: {result}")
        
        if result.startswith("Error"):
             with open("debug_error.log", "w", encoding="utf-8") as f:
                f.write(result)
                
    except Exception:
        # Capture full traceback and error message
        error_msg = traceback.format_exc()
        print("An error occurred. Writing to debug_error.log...")
        with open("debug_error.log", "w", encoding="utf-8") as f:
            f.write(error_msg)

if __name__ == "__main__":
    debug_hunyuan()
