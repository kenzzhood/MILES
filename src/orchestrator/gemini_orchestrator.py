"""
Gemini (Online API) Orchestrator Implementation.
"""

from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai

from .orchestrator import OrchestratorBase
from ..core.schemas import OrchestratorPlan

# This is the "System Prompt" that teaches the LLM how to be our Orchestrator.
# It uses Chain-of-Thought principles to force structured, decomposed output.
# This is the "System Prompt" that teaches the LLM how to be our Orchestrator.
# It uses Chain-of-Thought principles to force structured, decomposed output.
ORCHESTRATOR_SYSTEM_PROMPT = """
You are "MILES", a highly intelligent, conversational AI assistant.
Your goal is to help the user with their requests efficiently.

**Core Capabilities:**
1.  **Direct Conversation:** You can answer questions, write code, explain concepts, and chat normally.
2.  **Task Delegation:** You have access to specialist workers for heavy or specific tasks.

**Available Workers:**
- "3D_Generator": Generates a 3D model from an image file path. Use this when the user asks to "generate", "make", or "create" a 3D model, especially if they provide a file path or image.
- "RAG_Search": Performs a deep web search for factual information. Use this ONLY when you need up-to-date external information that you don't have.

**Decision Logic:**
- **IF** the user's request is simple, conversational, or something you can answer directly:
    - **DO NOT** assign any tasks.
    - Provide the answer in the `direct_response` field.
- **IF** the user wants to generate a 3D model (e.g., "make a 3d model of this image", "generate 3d"):
    - **Assign** "3D_Generator".
    - Set the `prompt` to the FILE PATH provided by the user (or the text description if no file).
- **IF** the user wants external info (e.g., "who won the game?", "latest news"):
    - **Assign** "RAG_Search".

**Output Format:**
Return **ONLY** a valid JSON object with this structure:
{
  "direct_response": "Your conversational response here (optional if tasks are present, required otherwise)",
  "tasks": [
    { "worker_name": "worker_name_1", "prompt": "specific_instructions_for_worker" }
  ]
}
"""


class GeminiOrchestrator(OrchestratorBase):
    """
    Orchestrator "brain" powered by the Gemini 1.5 Pro API.
    This provides maximum speed and reasoning power for development.
    """

    def __init__(self, api_key: str, model_name: str = "models/gemini-flash-latest"):
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            self.model_name = model_name
            print(f"[MILES] Brain Online: Using Google {model_name}")
        except Exception as exc:  # pragma: no cover - configuration errors surface at runtime
            print(f"Error initializing Gemini: {exc}")
            raise

    def decompose_task(self, user_prompt: str) -> OrchestratorPlan:
        """
        Analyzes the user's prompt and decides whether to answer directly,
        delegate to workers, or both.
        """

        print(f"Sending to Gemini: {user_prompt}")
        
        # We wrap the user prompt to ensure the model follows the system instructions
        chat = self.model.start_chat(history=[
            {"role": "user", "parts": [ORCHESTRATOR_SYSTEM_PROMPT]}
        ])
        
        try:
            response = chat.send_message(
                f"User Request: {user_prompt}\n\nRemember to return ONLY JSON.",
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                ),
            )

            json_text = response.text.strip().replace("```json", "").replace("```", "")
            print(f"[MILES] Gemini raw plan: {json_text}")
            plan_data: Any = json.loads(json_text)

            # Validate and normalize
            if "tasks" not in plan_data:
                plan_data["tasks"] = []
            
            return OrchestratorPlan(**plan_data)
        except Exception as exc:  # pragma: no cover - defensive fallback
            print(f"Error communicating with Gemini or parsing JSON: {exc}")
            print(f"Error communicating with Gemini or parsing JSON: {exc}")
            
            # Heuristic Fallback: Attempt to guess the intent
            lower_prompt = user_prompt.lower()
            if "generate" in lower_prompt or "make" in lower_prompt or "create" in lower_prompt:
                if "3d" in lower_prompt or ".png" in lower_prompt or ".jpg" in lower_prompt:
                     return OrchestratorPlan(
                        direct_response="Brain offline, fallback execution: Generating 3D Model...",
                        tasks=[{"worker_name": "3D_Generator", "prompt": user_prompt}]
                    )
            
            # Default Fallback: Web Search
            return OrchestratorPlan(
                direct_response="I'm having trouble processing that request. Let me try a search.",
                tasks=[{"worker_name": "RAG_Search", "prompt": user_prompt}]
            )

    def answer_prompt(self, user_prompt: str) -> str:
        """
        Legacy method. Now just delegates to decompose_task and returns the direct response.
        """
        plan = self.decompose_task(user_prompt)
        return plan.direct_response or "No response generated."

