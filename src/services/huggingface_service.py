"""
HuggingFace Image Generation Service

Uses HuggingFace SDXL Base 1.0 to generate 3D-ready images.
"""

from __future__ import annotations

import os
import uuid
import requests
from pathlib import Path


class HuggingFaceService:
    """Service for generating images using HuggingFace SDXL."""
    
    def __init__(self):
        from .. import config
        self.api_token = config.HUGGINGFACE_API_TOKEN
        
        if not self.api_token:
            raise RuntimeError(
                "Missing HUGGINGFACE_API_TOKEN in config.\n"
                "Add to .env: HUGGINGFACE_API_TOKEN=your_token_here"
            )
        
        self.api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        
        # Output directory
        self.output_dir = Path(__file__).resolve().parent.parent.parent / "outputs" / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def build_3d_ready_prompt(self, user_prompt: str) -> str:
        """
        Enhances user prompt with 3D-reconstruction-friendly instructions.
        """
        return (
            f"Generate a high-resolution, photorealistic image of a single {user_prompt}. "
            "Place the object perfectly centered on a pure white seamless background. "
            "Show the entire object fully in frame with no cropping. "
            "Use a neutral forward-facing 3/4 view. "
            "Lighting must be soft, even, and shadow-free. "
            "Do not include any text, reflections, props, shapes, patterns, accessories, or background elements. "
            "Keep edges crisp and clean. "
            "The object must be isolated and ideal for 3D reconstruction. "
            "The object should be highly detailed and intricately designed, showcasing fine textures and realistic features. "
            "Only a single object should be present in the image. "
            "Must be in 4k resolution. "
            "Must show the full object from top to bottom without any cropping."
        )
    
    def generate_image(self, prompt: str) -> str:
        """
        Generates a 3D-ready image from a text prompt.
        
        Args:
            prompt: User's object description
            
        Returns:
            Absolute path to the generated PNG file
        """
        final_prompt = self.build_3d_ready_prompt(prompt)
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        
        payload = {"inputs": final_prompt}
        
        print(f"[HuggingFace] Generating image for: '{prompt}'")
        print(f"[HuggingFace] Enhanced prompt: {final_prompt[:100]}...")
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code != 200:
                error_msg = f"HuggingFace API error: {response.status_code} - {response.text}"
                print(f"[HuggingFace] ERROR: {error_msg}")
                raise RuntimeError(error_msg)
            
            img_bytes = response.content
            
            # Save image
            image_id = str(uuid.uuid4())
            filename = f"{image_id}.png"
            save_path = self.output_dir / filename
            
            with open(save_path, "wb") as f:
                f.write(img_bytes)
            
            print(f"[HuggingFace] Image saved: {save_path}")
            return str(save_path.absolute())
            
        except Exception as e:
            print(f"[HuggingFace] Generation failed: {e}")
            raise


# Singleton instance
huggingface_service = HuggingFaceService()
