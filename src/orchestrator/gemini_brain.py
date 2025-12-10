"""
Gemini (Online API) Orchestrator Implementation.
"""

from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai

from .orchestrator import OrchestratorBase
from ..core.schemas import OrchestratorPlan
import time

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
- **IF** the user is REFINING a previous 3D request (e.g., "Make the handle gold", "Change it to red", "Add a texture", "Make it look old"):
    - **Assign** "3D_Generator".
    - **CRITICAL:** You MUST rewrite the prompt to be a fully independent description of the object.
    - **BAD:** "Make it red" (The image generator won't know what "it" is).
    - **GOOD:** "A medieval sword with a red handle" (Context integrated).
- **IF** the user wants specific *real-time* or *specialized* info (e.g., "who won the game last night?", "current stock price"):
    - **Assign** "RAG_Search".
- **IF** the user asks general knowledge (e.g., "capital of India", "who is Newton") or simple chat ("hi"):
    - **DO NOT** assign "RAG_Search". Answer directly.
    - **CRITICAL:** Do NOT assign "RAG_Search" unless the user explicitly uses keywords like "Research", "Find", "Search", "Deep Dive", "Look up", "Latest News".
    - If the user asks "What is X", just answer it. Do not search.

**Output Format:**
Return **ONLY** a valid JSON object with this structure:
{
  "direct_response": "Your conversational response here (optional if tasks are present, required otherwise)",
  "tasks": [
    { "worker_name": "worker_name_1", "prompt": "specific_instructions_for_worker" }
  ],
  "save_memory": false 
}
(Set "save_memory" to true ONLY if the user explicitly asks to SAVE the generated model permanently.)
"""


class GeminiOrchestrator(OrchestratorBase):
    """
    Orchestrator "brain" powered by the Gemini 1.5 Pro API.
    This provides maximum speed and reasoning power for development.
    """

    def __init__(self, api_keys: list[str] = None, model_name: str = "models/gemini-flash-latest"):
        from .. import config
        
        # Robust Key Loading: Combine args, config list, and single config
        keys = []
        if api_keys: keys.extend(api_keys)
        if config.GEMINI_API_KEYS: keys.extend(config.GEMINI_API_KEYS)
        if config.GEMINI_API_KEY: keys.append(config.GEMINI_API_KEY)
        
        # Deduplicate while preserving order
        self.api_keys = list(dict.fromkeys(keys))
        
        # Remove placeholders or empty strings
        self.api_keys = [k for k in self.api_keys if k and "YOUR_GEMINI" not in k]

        if not self.api_keys:
             raise ValueError("No valid GEMINI_API_KEYS found in config!")

        self.current_key_index = 0
        self.model_name = model_name
        self._configure_brain()

    def _configure_brain(self):
        """Initializes the Brain with the current key."""
        current_key = self.api_keys[self.current_key_index]
        try:
            genai.configure(api_key=current_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"[MILES] Brain Online (v2.0 - Strict Chat Mode): Using Google {self.model_name} (Key Index: {self.current_key_index})")
        except Exception as exc:
            print(f"Error initializing Gemini: {exc}")
            raise
    
    def _rotate_key(self):
        """Switches to the next API key in the list."""
        if len(self.api_keys) <= 1:
            print("[MILES] Only one key configured. Cannot rotate.")
            return False
            
        print(f"[MILES] Rate Limit Hit. Rotating Key (Cooling down for 2s)...")
        time.sleep(2) # Backoff to let the API breathe
        
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(f"[MILES] Rotation: Switching to Key Index {self.current_key_index}...")
        self._configure_brain()
        return True

    def decompose_task(self, user_prompt: str) -> OrchestratorPlan:
        """
        Analyzes the user's prompt and decides whether to answer directly,
        delegate to workers, or both.
        """

        print(f"Sending to Gemini: {user_prompt}")
        
        # Load history from MemoryManager
        from ..core.memory import memory
        history = memory.get_history()
        
        # Prepend system prompt if history is empty or just to be safe
        # (Gemini API handles system instructions differently in newer versions, 
        # but putting it as the first user message is a robust pattern for now)
        if not history:
             history = [{"role": "user", "parts": [ORCHESTRATOR_SYSTEM_PROMPT]}]
        else:
             # Ensure the system prompt is always known. 
             # We can't easily insert it at index 0 if the chat is long, but we can append a reminder
             # or rely on the fine-tuned instruction following.
             # Better: Just pass it in the `system_instruction` argument if supported, 
             # but here we follow the existing pattern.
             pass

        # Update memory with the new user prompt (so we remember it for next time)
        memory.add_message("user", user_prompt)
        
        # --- Pre-Flight Check 1: Force Routing for Obvious 3D Requests ---
        # The LLM can be inconsistent with "Negative Constraints" (e.g. "Don't use RAG for 'make'").
        # Enforce hard rule for 3D.
        lower_prompt = user_prompt.lower()
        
        creation_keywords = ["generate", "make", "create", "model", "render", "change", "turn", "convert"]
        target_keywords = ["3d", "image", "glb", "mesh", "object", "it", "this", "red", "blue", "green", "gold", "silver", "metal", "texture"]
        is_creation = any(k in lower_prompt for k in creation_keywords)
        has_target = any(k in lower_prompt for k in target_keywords)
        
        # Exclude search triggers from 3D check
        explicit_search_triggers = ["who", "when", "list of", "history of", "how to"]
        is_search_phrasing = any(k in lower_prompt for k in explicit_search_triggers)

        if is_creation and has_target and not is_search_phrasing:
             print(f"[MILES] Pre-Flight: '3D' detected ({user_prompt}). Using Brain to REWRITE prompt only.")
             
             # Rewriting logic (same as before)
             try:
                 rewrite_prompt = (
                     f"Rewrite this user request into a single, detailed visual description of the object. "
                     f"Ignore commands like 'make', 'change', 'generate'. Just describe the final object. "
                     f"If the user says 'Make it red', describe the previous object but red. "
                     f"User Request: {user_prompt}"
                 )
                 # Use a temporary chat to avoid polluting history with system instructions
                 # But we pass history to it so it knows context
                 chat_rewrite = self.model.start_chat(history=history)
                 response = chat_rewrite.send_message(rewrite_prompt)
                 refined_prompt = response.text.strip()
                 print(f"[MILES] Refined Prompt for 3D: '{refined_prompt}'")
             except Exception as e:
                 print(f"[MILES] Prompt Rewrite Failed: {e}. Using original.")
                 refined_prompt = user_prompt

             return OrchestratorPlan(
                direct_response=f"I'm on it. Generating: {refined_prompt}",
                tasks=[{"worker_name": "3D_Generator", "prompt": refined_prompt}]
            )

        # --- Pre-Flight Check 2: Direct Chat vs RAG Planner ---
        # If the user is NOT asking for 3D, are they asking for SEARCH?
        # If NOT search, we should just answer directly and skip the complex JSON planning overhead.
        
        search_intent_keywords = [
            "search", "find", "research", "lookup", "look up", 
            "news", "latest", "stock", "price", "weather", 
            "current", "live", "web", "internet", "google"
        ]
        
        
        # DEBUG: Find out WHAT matches
        matched_keywords = [k for k in search_intent_keywords if k in lower_prompt]
        is_explicit_search = len(matched_keywords) > 0
        
        from .. import config
        import importlib
        importlib.reload(config)
        self.api_keys = config.GEMINI_API_KEYS or [config.GEMINI_API_KEY]
        
        # --- HARD OVERRIDE for Greetings ---
        # Using 'in' instead of '==' to catch "hi.", "hi!", "hi there"
        if any(w in lower_prompt for w in ["hi", "hello", "hey", "test", "help"]):
            print(f"[DEBUG_BRAIN] Greeting detected. Forcing Direct Chat.")
            is_explicit_search = False

        print(f"[DEBUG_BRAIN] Prompt: '{user_prompt}'")
        print(f"[DEBUG_BRAIN] Keywords Matched: {matched_keywords}")
        print(f"[DEBUG_BRAIN] Search Mode: {is_explicit_search}")
        
        # If it's not 3D and NOT explicit search, treat as "Direct Conversation"
        # This prevents "Capital of India" -> RAG.
        if not is_explicit_search:
            print(f"[DEBUG_BRAIN] Routing to Direct Chat...")
            
            chat = self.model.start_chat(history=history)
            
            # Use Direct Text Mode (No JSON enforcement)
            max_retries = len(self.api_keys) + 1
            for attempt in range(max_retries):
                try:
                    # Provide a simple nudge to answer directly
                    response = chat.send_message(
                        f"{user_prompt}", 
                        # No generation_config forcing JSON
                    )
                    
                    # Logic to save the model's response to memory
                    memory.add_message("model", response.text)
                    
                    return OrchestratorPlan(
                        direct_response=response.text,
                        tasks=[]
                    )
                except Exception as e:
                    is_rate_limit = "429" in str(e) or "ResourceExhausted" in str(e)
                    if is_rate_limit:
                         print(f"[MILES] Rate Limit in Direct Chat. Rotating...")
                         if self._rotate_key():
                             # Re-instantiate chat with new model/key
                             chat = self.model.start_chat(history=history)
                             continue 
                    print(f"[MILES] Direct Chat Failed: {e}")
                    # If direct chat fails drastically, return a safe error
                    return OrchestratorPlan(direct_response="I'm having trouble connecting to my brain right now (Rate Limit or Error).", tasks=[])

        # --- Fallback: JSON Planner (Only for potential RAG / Ambiguous cases) ---
        print(f"[MILES_DEBUG_V3] JSON PLANNER ACTIVATED for '{user_prompt}'")
        chat = self.model.start_chat(history=history)
        
        # Retry loop for API Rotation (JSON Mode)
        max_retries = len(self.api_keys) + 1
        for attempt in range(max_retries):
            try:
                response = chat.send_message(
                    f"User Request: {user_prompt}\n\nRemember to return ONLY JSON.",
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json"
                    ),
                )
                break # Success
            except Exception as e:
                is_rate_limit = "429" in str(e) or "ResourceExhausted" in str(e) or "QuotaExceeded" in str(e)
                if is_rate_limit:
                     print(f"[MILES] Rate Limit (JSON). Rotating...")
                     if self._rotate_key():
                         chat = self.model.start_chat(history=history)
                         continue
                print(f"[MILES] Brain Error or Rotation Failed: {e}")
                # Don't raise, just let it fall to catch block
                break

        try:
            # Check if response exists (it might not if loop broke)
            if 'response' not in locals():
                 raise Exception("No response from Gemini (All keys exhausted?)")

            json_text = response.text.strip().replace("```json", "").replace("```", "")
            plan_data: Any = json.loads(json_text)
            
            if "tasks" not in plan_data: plan_data["tasks"] = []
            
            # Save response
            if plan_data.get("direct_response"):
                memory.add_message("model", plan_data["direct_response"])

            if plan_data.get("save_memory") and memory.active_session_files:
                last_file = memory.active_session_files[-1]
                saved_path = memory.save_model_permanently(os.path.basename(last_file))
                if saved_path: memory.add_message("model", f"System: Model saved to {saved_path}")

            return OrchestratorPlan(**plan_data)
        
        except Exception as exc:
             print(f"[MILES_DEBUG_V3] JSON Parsing Failed: {exc}. Fallback Logic.")
             # DISABLE RAG FALLBACK for safety.
             # If the brain is broken, we should not burn tokens on RAG.
             return OrchestratorPlan(
                direct_response="My brain is tired (Rate Limit Reached). Please check API keys.",
                tasks=[]
            )

    def answer_prompt(self, user_prompt: str) -> str:
        """
        Legacy method. Now just delegates to decompose_task and returns the direct response.
        """
        plan = self.decompose_task(user_prompt)
        return plan.direct_response or "No response generated."

