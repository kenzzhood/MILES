import os
import subprocess
import time
import json
import logging
import requests
import websocket # type: ignore
import uuid
import rembg
from PIL import Image
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

class SF3DService:
    """
    Manages the Stable Fast 3D (ComfyUI) background service.
    Handles lifecycle (start/stop) and API communication (generate 3D).
    """

    def __init__(self):
        # Paths
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.portable_root = os.path.join(self.project_root, "src", "libs", "SF3D_Portable", "SF3D", "SF3D")
        self.run_bat = os.path.join(self.portable_root, "run.bat")
        
        # ComfyUI API
        self.base_url = "http://127.0.0.1:8188"
        self.ws_url = "ws://127.0.0.1:8188/ws"
        
        # Process handle
        self.process: Optional[subprocess.Popen] = None

    def start_service(self) -> bool:
        """Starts the ComfyUI background service if not already running."""
        if self.is_healthy():
            logger.info("SF3D Service already running.")
            return True

        logger.info(f"Starting SF3D Service from: {self.run_bat}")
        
        try:
            # Start as a detached process (hidden window)
            # CREATE_NO_WINDOW = 0x08000000
            # DETACHED_PROCESS = 0x00000008
            flags = subprocess.CREATE_NO_WINDOW 
            
            self.process = subprocess.Popen(
                [self.run_bat],
                cwd=self.portable_root,
                creationflags=flags,
                shell=True,
                stdout=subprocess.DEVNULL, # Mute output
                stderr=subprocess.DEVNULL
            )
            
            # Wait for startup
            logger.info("Waiting for SF3D Service to become healthy...")
            for _ in range(30):  # Wait up to 60s
                if self.is_healthy():
                    logger.info("SF3D Service Started Successfully.")
                    return True
                time.sleep(2)
            
            logger.error("SF3D Service failed to start (timeout).")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start SF3D Service: {e}")
            return False

    def stop_service(self):
        """Stops the background service."""
        if self.process:
            logger.info("Stopping SF3D Service...")
            # Ideally we should find the full process tree, but for now we let it run 
            # or kill the Popen object. Since it's a batch file, killing Popen might just kill cmd.exe
            # For a proper kill, we might need psutil, but let's try basic terminate.
            self.process.terminate()
            self.process = None

    def is_healthy(self) -> bool:
        """Checks if the ComfyUI API is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/", timeout=1)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def upload_image(self, image_path: str) -> str:
        """Uploads an image to ComfyUI and returns the filename."""
        url = f"{self.base_url}/upload/image"
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {'type': 'input', 'overwrite': 'true'}
            resp = requests.post(url, files=files, data=data)
            resp.raise_for_status()
            return resp.json()['name']
    
    def _remove_background(self, input_path: str) -> str:
        """Removes background locally using rembg and saves a temp file."""
        logger.info(f"Removing background from {input_path}")
        try:
            img = Image.open(input_path)
            output = rembg.remove(img)
            
            # Save processed image
            temp_dir = os.path.join(self.portable_root, "ComfyUI", "input") # Use Comfy input dir to avoid upload?
            # Or just save beside input
            processed_filename = f"processed_{uuid.uuid4().hex}.png"
            # Note: We still use upload_image which uploads from local path.
            # So saving it casually is fine.
            # Better: Save to a temp folder in the project.
            
            # Actually, let's keep it simple: Save in the same dir as input
            processed_path = os.path.join(os.path.dirname(input_path), processed_filename)
            output.save(processed_path)
            return processed_path
        except Exception as e:
            logger.error(f"Failed to remove background: {e}")
            return input_path # Fallback to original

    def generate_model(self, image_path: str) -> Optional[str]:
        """
        Full pipeline: Remove BG -> Upload -> Construct Workflow -> Queue -> Wait -> Return path.
        """
        if not self.start_service():
            return None

        try:
            # 0. Remove Background (NEW)
            processed_path = self._remove_background(image_path)
            
            # 1. Upload Image
            filename = self.upload_image(processed_path)
            logger.info(f"Image uploaded: {filename}")
            
            # Cleanup temp processed file? 
            # Maybe keep it for debugging or delete it.
            # os.remove(processed_path) 

            # 2. Construct Workflow (Dynamic JSON)
            client_id = str(uuid.uuid4())
            prompt_workflow = self._build_workflow(filename)

            # 3. Connection to WebSocket for status updates
            ws = websocket.WebSocket()
            ws.connect(f"{self.ws_url}?clientId={client_id}")

            # 4. Queue Prompt
            p = {"prompt": prompt_workflow, "client_id": client_id}
            resp = requests.post(f"{self.base_url}/prompt", json=p)
            resp.raise_for_status()
            prompt_id = resp.json()['prompt_id']
            logger.info(f"Prompt queued: {prompt_id}")

            # 5. Wait for completion
            output_filename = None
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            logger.info("Execution complete!")
                            break # Execution done
            
            # 6. Retrieve Output File Path
            # We know the output node ID is 9 (StableFast3DSave)
            # But ComfyUI history API is better source of truth
            history_url = f"{self.base_url}/history/{prompt_id}"
            h_resp = requests.get(history_url)
            h_data = h_resp.json()[prompt_id]
            
            # Parse output
            # outputs: { "9": { "glbs": ["...base64..."] } } - Wait, the node returns base64 in UI?
            # The Save node usually writes to disk.
            # Let's check the disk output folder.
            
            # HACK: The node writes to specific folder. 
            # We can construct the path or look at the history if it returns filenames.
            # Standard SaveImage returns filenames. SF3DSave returns "glbs" list.
            # Let's verify by checking the output directory for the newest file.
            
            output_dir = os.path.join(self.portable_root, "ComfyUI", "output")
            # Find newest .glb file
            glb_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.glb')]
            if glb_files:
                newest_file = max(glb_files, key=os.path.getctime)
                return newest_file
            
            return None

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return None
        finally:
            if 'ws' in locals():
                ws.close()

    def _build_workflow(self, image_filename: str) -> Dict[str, Any]:
        """
        Constructs the ComfyUI workflow JSON programmatically.
        Includes RemBG for background removal.
        """
        # Node Layout
        # 1: LoadImage
        # 2: ImageRembg (NEW)
        # 7: StableFast3DLoader
        # 8: StableFast3DSampler
        # 9: StableFast3DSave
        
        workflow = {
            "1": {
                "inputs": {
                    "image": image_filename,
                    "upload": "image"
                },
                "class_type": "LoadImage",
                "_meta": {"title": "Load Image"}
            },
            "6": {
                "inputs": {
                    "mask": ["1", 1] # Link to LoadImage (MASK)
                },
                "class_type": "InvertMask",
                "_meta": {"title": "Invert Mask"}
            },
            "7": {
                "inputs": {
                    "config_name": "config.yaml",
                    "weight_name": "model.safetensors"
                },
                "class_type": "StableFast3DLoader",
                "_meta": {"title": "Stable Fast 3D Loader"}
            },
            "8": {
                "inputs": {
                    "foreground_ratio": 0.85,
                    "texture_resolution": 1024,
                    "remesh": "triangle",
                    "vertex_count": -1,
                    "model": ["7", 0], # Link to Loader
                    "image": ["1", 0], # Link to LoadImage (IMAGE)
                    "mask":  ["6", 0]  # Link to InvertMask
                },
                "class_type": "StableFast3DSampler",
                "_meta": {"title": "Stable Fast 3D Sampler"}
            },
            "9": {
                "inputs": {
                    "filename_prefix": "SF3D_API",
                    "mesh": ["8", 0] # Link to Sampler
                },
                "class_type": "StableFast3DSave",
                "_meta": {"title": "Stable Fast 3D Save"}
            }
        }
        return workflow

# Singleton instance
sf3d_service = SF3DService()
