"""
Specialist Worker: 3D Content Generation (Local - Stable Fast 3D)

This worker uses the local SF3D service (ComfyUI backend) to generate 3D meshes.
"""

from __future__ import annotations

import os
from pathlib import Path

# Local utils
from .celery_app import celery_app
from ..services.sf3d_service import sf3d_service

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

@celery_app.task(name="tasks.generate_3d_model")
def generate_3d_model(prompt: str) -> str:
    """
    Generates a 3D model using the local SF3D Service.
    
    Args:
        prompt: Filepath to the input image. (Future: Text prompt if T2I is added)
    """
    print(f"STARTING 3D_Generator (SF3D Local): '{prompt}'")
    
    image_path = prompt
    
    # Validation
    if not os.path.exists(image_path):
        # Fallback for testing or if prompt is text
        print(f"Input '{image_path}' is not a file. Checking known test images...")
        # (Optional: Add fallback logic here)
        return f"Error: Input image not found at '{image_path}'. Please provide a valid file path."

    try:
        print("Delegating to SF3DService...")
        glb_path = sf3d_service.generate_model(image_path)
        
        if not glb_path:
            return "Error: SF3D Service returned no result. Check the console window for crashes."
            
        filename = os.path.basename(glb_path)
        
        # We assume the service returns the full path in the portable output dir.
        # We can link it or copy it to the models dir for the web UI.
        target_path = MODELS_DIR / filename
        
        # Copy/Move file to accessible models directory
        import shutil
        shutil.copy(glb_path, target_path)
        
        print(f"Model available at: {target_path}")
        return f"3D Model Generated (SF3D). [View Model](/models/{filename})"

    except Exception as e:
        print(f"SF3D Worker Error: {e}")
        return f"Error executing SF3D generation: {e}"
