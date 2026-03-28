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
    
    # Determine if prompt is a file path or a text description
    image_path = prompt
    is_text_prompt = not os.path.exists(image_path) and not image_path.startswith("http")
    
    # Lazy import to avoid circular dependencies if any
    from ..services.image_gen_service import image_gen_service
    from ..core.memory import memory

    if is_text_prompt:
        # Always generate a fresh concept image for each new prompt.
        # Reusing a previous image caused wrong models to appear (e.g. "apple" refining "robot").
        # Explicit refinement (e.g. "make it red") should be handled by the brain
        # by rewriting the full description, not by reusing the old image.
        try:
            print(f"Generating new concept image for: '{prompt}'...")
            image_path = image_gen_service.generate_image(prompt)
            print(f"Concept image generated at: {image_path}")
        except Exception as e:
            return f"Error generating concept image: {e}"

    if not os.path.exists(image_path):
        return f"Error: Input image not found at '{image_path}'. Please provide a valid file path or text description."

    try:
        print("Delegating to SF3DService...")
        glb_path = sf3d_service.generate_model(image_path)
        
        if not glb_path:
            return "Error: SF3D Service returned no result. Check the console window for crashes."
            
        filename = os.path.basename(glb_path)
        
        # Register the generated model in memory (temp by default)
        memory.register_file(glb_path, is_temp=True)

        # Copy to accessible models directory (so the UI can see it)
        # We treat the 'models' dir as a cache/staging area too.
        # True persistence only happens if user asks to 'save'.
        target_path = MODELS_DIR / filename
        import shutil
        shutil.copy(glb_path, target_path)
        
        print(f"Model available at: {target_path}")
        
        # --- Hologram Display Integration ---
        # Automatically broadcast to connected hologram displays
        try:
            import requests
            import time as _time
            broadcast_url = "http://localhost:8001/hologram/broadcast"
            # Add timestamp cache-buster so the browser always fetches the new model
            cache_buster = int(_time.time())
            model_url = f"/models/{filename}?v={cache_buster}"
            
            payload = {
                "type": "load_model",
                "data": {"url": model_url}
            }
            
            print(f"[HOLOGRAM] Broadcasting model to displays: {model_url}")
            response = requests.post(broadcast_url, json=payload, timeout=2)
            
            if response.status_code == 200:
                print(f"[HOLOGRAM] ✓ Model sent to display successfully!")
            else:
                print(f"[HOLOGRAM] Warning: Broadcast failed ({response.status_code})")
        except Exception as broadcast_err:
            # Don't fail the whole task if broadcast fails
            print(f"[HOLOGRAM] Could not broadcast (display may not be connected): {broadcast_err}")
        
        # Return a rich response with the image and model
        return (
            f"**3D Model Generated**\n\n"
            f"Concept Image used: {os.path.basename(image_path)}\n"
            f"Model: [View Model](/models/{filename})"
        )

    except Exception as e:
        print(f"SF3D Worker Error: {e}")
        return f"Error executing SF3D generation: {e}"
