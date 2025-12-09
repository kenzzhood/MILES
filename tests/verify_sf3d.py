
import sys
import os
import torch

# Add the library path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src/libs/stable-fast-3d'))

try:
    print("Attempting to import sf3d...")
    from sf3d.system import SF3D
    print("Successfully imported SF3D.")
except ImportError as e:
    print(f"Failed to import SF3D: {e}")
    sys.exit(1)

try:
    print("Checking CUDA availability...")
    if torch.cuda.is_available():
        print(f"CUDA is available: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA is NOT available. SF3D might run slowly or fail.")
except Exception as e:
    print(f"Error checking CUDA: {e}")

print("SF3D setup seems correct (imports working).")
