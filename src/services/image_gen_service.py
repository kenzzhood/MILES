"""
Image Generation Service (HuggingFace SDXL)

Uses the User-provided logic to generate 3D-ready assets.
"""

import os
import uuid
import requests
import logging
from dotenv import load_dotenv

# Load ENV (ensure this is called early)
load_dotenv()

logger = logging.getLogger(__name__)

from src.core.memory import memory

class ImageGenService:
    def __init__(self):
        # We look for the token in the environment variable loaded from src/.env
        # Note: In main.py, we might want to load .env explictly if not handled.
        self.api_token = os.getenv("HUGGINGFACE_API_TOKEN")
        
        # Fallback/Check
        if not self.api_token:
            logger.warning("HUGGINGFACE_API_TOKEN is missing. Image generation will fail.")

        self.api_url = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
        
        # Paths
        self.output_dir = os.path.join("src", "data", "tmp", "images") # Use TMP dir logic
        os.makedirs(self.output_dir, exist_ok=True)

    def build_3d_ready_prompt(self, user_prompt: str) -> str:
        """
        Expands the user prompt to ensure 3D readiness, based on user requirements.
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
            "Only single object should be present in the image. "
            "Must be in 4k resolution. "
            "Must show the full object from top to bottom without any cropping."
        )

    def generate_image(self, prompt: str) -> str:
        """
        Generates an image from text. Returns the local file path.
        """
        if not self.api_token:
             raise RuntimeError("HUGGINGFACE_API_TOKEN not configured.")

        final_prompt = self.build_3d_ready_prompt(prompt)
        logger.info(f"Generating Image with Prompt: {final_prompt}")

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        
        payload = {"inputs": final_prompt}

        response = requests.post(self.api_url, headers=headers, json=payload)

        if response.status_code != 200:
            logger.error(f"HF API Error: {response.text}")
            raise RuntimeError(f"Image Generation Failed: {response.text}")

        img_bytes = response.content
        
        image_id = str(uuid.uuid4())
        filename = f"{image_id}.png"
        save_path = os.path.abspath(os.path.join(self.output_dir, filename))

        with open(save_path, "wb") as f:
            f.write(img_bytes)
            
        logger.info(f"Image saved to: {save_path}")
        
        # Register with memory to track it as a temp file
        memory.register_file(save_path, is_temp=True)
        
        return save_path

    def refine_image(self, base_image_path: str, prompt: str) -> str:
        """
        Uses an existing image as a reference to generate a variation (Img2Img).
        """
        if not self.api_token:
             raise RuntimeError("HUGGINGFACE_API_TOKEN not configured.")

        # We can use the Refiner model or just the Base model with image input
        # For simplicity and robustness with standard APIs, we'll try the Base model with image input 
        # but the Refiner is specifically designed for this.
        # Let's use the refiner URL.
        refiner_url = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-refiner-1.0"
        
        final_prompt = self.build_3d_ready_prompt(prompt)
        logger.info(f"Refining Image {base_image_path} with: {final_prompt}")

        headers = {
            "Authorization": f"Bearer {self.api_token}",
             # Content-Type typically automatically handled when sending files/bytes via specific libs
             # But for raw HTTP to inference API, it depends.
             # Standard HF Inference API for Img2Img usually expects the binary image data 
             # OR a JSON with inputs as base64.
             # Let's try the modern InferenceClient approach if available, or just raw bytes.
             # Using "huggingface_hub" InferenceClient is safest if available in environment.
             # Since user didn't give it, we will use the standard "inputs" parameter.
        }
        
        # Read image bytes
        with open(base_image_path, "rb") as f:
            image_bytes = f.read()

        # The HF Inference API is tricky with Img2Img via raw HTTP. 
        # Often it's easier to use the `huggingface_hub` library.
        # Let's try to import it, it should be in the environment if pandas/etc are there.
        # If not, we'll fallback to T2I with prompt injection of "similar to X".
        
        try:
            from huggingface_hub import InferenceClient
            # FORCE the new Router URL to bypass 410 Deprecated error
            client = InferenceClient(model=self.api_url, token=self.api_token)
            
            # Using the base model for Img2Img is often better for big changes than the refiner
            image = client.image_to_image(
                prompt=final_prompt,
                image=image_bytes, 
                model="stabilityai/stable-diffusion-xl-base-1.0",
                strength=0.75 # Allow significant changes (0.0 = no change, 1.0 = full replacement)
            )
            
            image_id = str(uuid.uuid4())
            filename = f"{image_id}.png"
            save_path = os.path.abspath(os.path.join(self.output_dir, filename))
            image.save(save_path)
            
            logger.info(f"Refined Image saved to: {save_path}")
            memory.register_file(save_path, is_temp=True)
            return save_path

        except ImportError:
            logger.warning("huggingface_hub not installed. Falling back to Text-to-Image.")
            return self.generate_image(prompt)
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            if "410 Client Error" in str(e) or "404 Client Error" in str(e):
                 logger.warning("Img2Img Endpoint deprecated or unavailable. Falling back to clean Text-to-Image generation.")
                 # Fallback: Just generate new image using T2I (which is robust)
                 return self.generate_image(prompt)
            raise

image_gen_service = ImageGenService()
