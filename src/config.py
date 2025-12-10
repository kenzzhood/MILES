"""
Configuration for the MILES Project.

This file contains the master switch for selecting the Orchestrator's "brain."
"""

# Set to "DEMO" for the deterministic mock brain.
# Set to "GEMINI" to use the fast, powerful online API.
# Set to "LOCAL" to use the free, private, local Ollama model.
# This "swappable brain" design is a key feature of the MILES architecture.
BRAIN_MODE = "GEMINI"

# --- API Keys ---
# !! IMPORTANT: Never commit real API keys to Git.
# !! Use environment variables in a real application.
# !! For this research prototype, we place it here for simplicity.
GEMINI_API_KEY = "AIzaSyCXvH2GY3yJK9qN947nBwL8LDljIMRCE_0"
GEMINI_API_KEYS = [
    "AIzaSyCXvH2GY3yJK9qN947nBwL8LDljIMRCE_0", # Primary (Good)
    "AIzaSyA65YZ5QGt4ZWMf1WO1lri-vGccIIDxrIE", # Secondary (Limited)
]
GEMINI_MODEL_NAME = "models/gemini-flash-latest"
TAVILY_API_KEY = "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"

# --- Local Model Config ---
# Ensure you have run 'ollama run llama3.1:8b' in your terminal
LOCAL_MODEL_NAME = "llama3.1:8b"

# --- Task Queue Config ---
REDIS_BROKER_URL = "redis://localhost:6379/0"
REDIS_BACKEND_URL = "redis://localhost:6379/1"

# Tencent Cloud Credentials
TENCENT_SECRET_ID = "IKIDmoeFcoMm6KMCp6B7uXzqdEahmkdXdAiD"
TENCENT_SECRET_KEY = "X1Uq8Mj8VvT4iPBAza9nWG50x0DU9tbF"
TENCENT_REGION = "ap-shanghai"

