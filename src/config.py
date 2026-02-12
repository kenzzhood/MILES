"""
Configuration for the MILES Project.

This file contains the master switch for selecting the Orchestrator's "brain."
"""
import os
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"  # src/.env
load_dotenv(dotenv_path=env_path)

# Set to "DEMO" for the deterministic mock brain.
# Set to "GEMINI" to use the fast, powerful online API.
# Set to "LOCAL" to use the free, private, local Ollama model.
# This "swappable brain" design is a key feature of the MILES architecture.
BRAIN_MODE = "GEMINI"

# --- API Keys ---
# !! IMPORTANT: Never commit real API keys to Git.
# !! Use environment variables in a real application.
# !! For this research prototype, we place it here for simplicity.
GEMINI_API_KEY = "AIzaSyAjeopVfyu1qlyvxOQYoORVgWASMXMHT3w"
GEMINI_API_KEYS = [
    "AIzaSyAjeopVfyu1qlyvxOQYoORVgWASMXMHT3w", # Primary (Good)
    "AIzaSyBF2qzGeH_yFKGWxOxniiZIrukht10jpEc", # Secondary (Limited)
]
GEMINI_MODEL_NAME = "models/gemini-flash-latest"
TAVILY_API_KEY = "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"

# HuggingFace API Token (for SDXL Image Generation)
HUGGINGFACE_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "")

# --- Local Model Config ---
# Ensure you have run 'ollama run llama3.1:8b' in your terminal
LOCAL_MODEL_NAME = "llama3.1:8b"

# --- Task Queue Config ---
REDIS_BROKER_URL = "redis://localhost:6379/0"
REDIS_BACKEND_URL = "redis://localhost:6379/1"

# Tencent Cloud Credentials
TENCENT_SECRET_ID = os.environ.get("TENCENT_SECRET_ID", "")
TENCENT_SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY", "")
TENCENT_REGION = "ap-shanghai"
