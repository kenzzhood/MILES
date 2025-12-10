"""
MILES Memory Manager

Handles:
1.  **Short-term Conversation History**: For context-aware multi-turn conversations.
2.  **File Lifecycle Management**: Tracking generated files (images/models) and managing their
    persistence (temp vs. saved).
"""

import os
import json
import shutil
import time
from typing import List, Dict, Optional, Any
from pathlib import Path

# Constants
MEMORY_FILE = os.path.join("src", "data", "memory.json")
TMP_DIR = os.path.join("src", "data", "tmp")
SAVED_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "models") # Root/models

class MemoryManager:
    def __init__(self):
        self._ensure_dirs()
        self.history: List[Dict[str, Any]] = []
        self.active_session_files: List[str] = [] # List of file paths generated in this session
        self._load_memory()

    def _ensure_dirs(self):
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        os.makedirs(TMP_DIR, exist_ok=True)
        os.makedirs(SAVED_MODELS_DIR, exist_ok=True)

    def _load_memory(self):
        """Loads conversation history from disk."""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.history = data.get("history", [])
            except Exception as e:
                print(f"[Memory] Failed to load memory: {e}")
                self.history = []

    def save_memory(self):
        """Persists conversation history to disk."""
        try:
            with open(MEMORY_FILE, 'w') as f:
                json.dump({"history": self.history}, f, indent=2)
        except Exception as e:
            print(f"[Memory] Failed to save memory: {e}")

    def add_message(self, role: str, content: str):
        """Adds a message to the conversation history."""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        # Keep window (e.g., last 50 messages)
        if len(self.history) > 50:
            self.history.pop(0)
        self.save_memory()

    def get_history(self) -> List[Dict[str, str]]:
        """Returns the conversation history formatted for the LLM."""
        return [{"role": m["role"], "parts": [m["content"]]} for m in self.history]

    def register_file(self, file_path: str, is_temp: bool = True):
        """
        Registers a generated file. 
        If is_temp is True, it will be cleaned up unless saved later.
        """
        if is_temp:
            self.active_session_files.append(file_path)

    def save_model_permanently(self, filename: str) -> str:
        """
        Moves a file from tmp (or wherever) to the saved models directory.
        Returns the new path.
        """
        # Find the file in active session or tmp
        source_path = None
        for path in self.active_session_files:
            if os.path.basename(path) == filename:
                source_path = path
                break
        
        if not source_path and os.path.exists(os.path.join(TMP_DIR, filename)):
            source_path = os.path.join(TMP_DIR, filename)

        if source_path and os.path.exists(source_path):
            target_path = os.path.join(SAVED_MODELS_DIR, filename)
            shutil.copy2(source_path, target_path)
            print(f"[Memory] Saved model to {target_path}")
            return target_path
        
        return ""

    def cleanup_session(self):
        """
        Deletes temporary files tracked in this session.
        This should be called when a "chat" ends or explicitly by the user (rare/complex to define 'end').
        For now, we might provide a tool to call this.
        """
        for file_path in self.active_session_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"[Memory] Cleaned up {file_path}")
                except Exception as e:
                    print(f"[Memory] Error cleaning up {file_path}: {e}")
        self.active_session_files = []

# Singleton
memory = MemoryManager()
