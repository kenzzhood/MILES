
import sys
import os
import torch
import time
from pathlib import Path

# Add project root and TripoSR path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRIPOSR_PATH = PROJECT_ROOT / "src" / "libs" / "TripoSR"
sys.path.append(str(TRIPOSR_PATH))

print(f"Project Root: {PROJECT_ROOT}")
print(f"TripoSR Path: {TRIPOSR_PATH}")

try:
    from tsr.system import TSR
    print("TripoSR imported successfully.")
except ImportError as e:
    print(f"Failed to import TripoSR: {e}")
    sys.exit(1)

def debug_load_model():
    print("Checking CUDA...")
    if torch.cuda.is_available():
        print(f"CUDA Available: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA NOT Available. Using CPU (Will be slow).")

    print("\n--- STARTING MODEL LOAD ---")
    start_time = time.time()
    
    try:
        # Load from pretrained
        # This is where it likely hangs if download stalls
        model = TSR.from_pretrained(
            "stabilityai/TripoSR",
            config_name="config.yaml",
            weight_name="model.ckpt",
        )
        print(f"Model loaded successfully in {time.time() - start_time:.2f}s")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        print(f"Model moved to {device}")

    except Exception as e:
        print(f"Error loading model: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_load_model()
