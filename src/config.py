"""
Configuration for the MILES Project.

This file contains the master switch for selecting the Orchestrator's "brain."
"""
import os

# Set to "DEMO" for the deterministic mock brain.
# Set to "GEMINI" to use the fast, powerful online API.
# Set to "LOCAL" to use the free, private, local Ollama model.
# This "swappable brain" design is a key feature of the MILES architecture.
BRAIN_MODE = "GEMINI"

# --- API Keys ---
# !! IMPORTANT: Never commit real API keys to Git.
# !! Use environment variables in a real application.
# !! For this research prototype, we place it here for simplicity.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_GOES_HERE")
# Load multiple keys for rotation if available (comma-separated)
GEMINI_API_KEYS = os.environ.get("GEMINI_API_KEYS", "").split(",") if os.environ.get("GEMINI_API_KEYS") else []
GEMINI_MODEL_NAME = "models/gemini-flash-latest"
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "YOUR_TAVILY_API_KEY_HERE")

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
