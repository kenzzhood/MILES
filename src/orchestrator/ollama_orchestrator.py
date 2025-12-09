"""
Ollama (Local Model) Orchestrator Implementation.
"""

from __future__ import annotations

import json
from typing import Any, Dict

import ollama

from .orchestrator import OrchestratorBase
from ..core.schemas import OrchestratorPlan

# This is the "System Prompt" formatted for local Ollama chat.
OLLAMA_SYSTEM_MESSAGE: Dict[str, str] = {
    "role": "system",
    "content": """
You are the central Orchestrator for the "MILES" intelligent assistant.
Your sole responsibility is to decompose a complex user request into a JSON list of sub-tasks for specialist workers.

You have the following workers available:
- "3D_Generator": Takes a text description and generates a 3D model.
- "RAG_Search": Takes a text query and performs a web search (RAG) to find factual information.
- "Hologram_Manipulator": Takes an action (e.g., "rotate", "scale") and applies it to the current hologram.

The user's request will follow.
Return *ONLY* the valid JSON plan.
""",
}


class OllamaOrchestrator(OrchestratorBase):
    """
    Orchestrator "brain" powered by a local Ollama model.
    This provides a free, private, and offline-capable "brain".
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        print(f"[MILES] Brain Local: Using Ollama model '{self.model_name}'")

    def decompose_task(self, user_prompt: str) -> OrchestratorPlan:
        """
        Decomposes the user's prompt using the local Ollama model.
        """

        print(f"Sending to Ollama: {user_prompt}")

        try:
            user_message = {"role": "user", "content": user_prompt}
            response = ollama.chat(
                model=self.model_name,
                messages=[OLLAMA_SYSTEM_MESSAGE, user_message],
                format="json",  # We ask Ollama to guarantee JSON output
            )

            json_text = response["message"]["content"]
            plan_data: Any = json.loads(json_text)

            return OrchestratorPlan(**plan_data)
        except Exception as exc:  # pragma: no cover - fallback for local model issues
            print(f"Error communicating with Ollama or parsing JSON: {exc}")
            return OrchestratorPlan(tasks=[{"worker_name": "RAG_Search", "prompt": user_prompt}])  # type: ignore[arg-type]

    def answer_prompt(self, user_prompt: str) -> str:
        """
        Generate a direct answer via the local Ollama model.
        """

        response = ollama.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are MILES, respond directly and concisely.",
                },
                {"role": "user", "content": user_prompt},
            ],
        )
        return response["message"]["content"]

