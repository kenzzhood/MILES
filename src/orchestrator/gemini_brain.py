"""
Gemini (Online API) Orchestrator — Production v3.1
Clean routing: deterministic pre-flight for 3D + strict keyword gate for RAG.
ALL chat goes through JSON mode so there's never raw JSON in the UI.
History is NOT sent to the JSON planner (avoids re-running old plans).
"""

from __future__ import annotations

import json
import re
from typing import Any

import google.generativeai as genai

from .orchestrator import OrchestratorBase
from ..core.schemas import OrchestratorPlan
import time


ORCHESTRATOR_SYSTEM_PROMPT = """
You are "MILES", a conversational AI assistant. Reply naturally and helpfully.

You have two specialist workers available:
- "3D_Generator": Generates a 3D model from a text description. Use ONLY when user explicitly asks to generate/create/make a 3D model.
- "RAG_Search": Performs a web search. Use ONLY when user explicitly uses words like "research", "search for", "look up", "find me news about", "latest", etc.

For ALL other requests (greetings, factual questions, general chat, explanations):
- Answer directly in "direct_response"
- Leave "tasks" as an empty list []
- NEVER use workers for general knowledge questions

Always return ONLY valid JSON in this exact format:
{
  "direct_response": "Your plain text answer here, or null if you are dispatching a task",
  "tasks": []
}

RULES:
- "direct_response" must be a plain human-readable string, NEVER JSON
- Do NOT dispatch workers for greetings, simple questions, facts, or explanations
- Do NOT add tasks when answering a direct question
"""


class GeminiOrchestrator(OrchestratorBase):

    def __init__(self, api_keys: list[str] = None, model_name: str = "models/gemini-flash-latest"):
        from .. import config

        keys = []
        if api_keys:
            keys.extend(api_keys)
        if config.GEMINI_API_KEYS:
            keys.extend(config.GEMINI_API_KEYS)
        if config.GEMINI_API_KEY:
            keys.append(config.GEMINI_API_KEY)

        self.api_keys = list(dict.fromkeys(keys))
        self.api_keys = [k for k in self.api_keys if k and "YOUR_GEMINI" not in k]

        if not self.api_keys:
            # Fallback if no keys provided so test doesn't crash on init without API keys.
            self.api_keys = ["YOUR_GEMINI_API_KEY_GOES_HERE"]

        self.current_key_index = 0
        self.model_name = model_name
        self._configure_brain()

    def _configure_brain(self):
        current_key = self.api_keys[self.current_key_index]
        genai.configure(api_key=current_key)
        self.model = genai.GenerativeModel(
            self.model_name,
            system_instruction=ORCHESTRATOR_SYSTEM_PROMPT
        )
        print(f"[MILES] Brain Online (v3.1): {self.model_name} (Key {self.current_key_index})")

    def _rotate_key(self) -> bool:
        if len(self.api_keys) <= 1:
            return False
        time.sleep(2)
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._configure_brain()
        return True

    # ── Deterministic 3D pre-flight ──────────────────────────────────────────
    _3D_VERBS = {"generate", "make", "create", "build", "produce", "render"}
    _3D_NOUNS = {"3d", "model", "glb", "mesh", "hologram"}

    def _is_3d_request(self, prompt: str) -> bool:
        words = set(prompt.lower().split())
        return bool(words & self._3D_VERBS) and bool(words & self._3D_NOUNS)

    def _extract_object_name(self, prompt: str) -> str:
        lower = prompt.lower()
        m = re.search(r'\bof\s+(?:a\s+|an\s+)?(.+)', lower)
        if m:
            obj = m.group(1).strip()
        else:
            obj = lower
            for word in ["generate", "make", "create", "build", "produce", "render",
                         "3d model", "3d", "model", "glb", "me", "a", "an", "the"]:
                obj = obj.replace(word, " ")
            obj = " ".join(obj.split())
        return obj.rstrip(".,!?") or prompt

    # ── Deterministic RAG pre-flight ─────────────────────────────────────────
    # Only explicit search phrasing triggers RAG — not just the word "research" alone
    _RAG_PATTERNS = [
        r'\bsearch\s+(for|about|on)\b',
        r'\blook\s+up\b',
        r'\bfind\s+(me\s+)?(news|info|information|latest)\b',
        r'\bconduct\s+a?\s*research\b',
        r'\bdo\s+a?\s*research\b',
        r'\bweb\s+search\b',
        r'\blatest\s+news\b',
    ]

    def _is_rag_request(self, prompt: str) -> bool:
        lower = prompt.lower()
        return any(re.search(pat, lower) for pat in self._RAG_PATTERNS)

    def _extract_rag_query(self, prompt: str) -> str:
        """Strip command words from RAG prompt to get the search query."""
        lower = prompt.lower()
        # Remove all trigger phrases
        for pat in [r'conduct\s+a?\s*research\s+(on\s+)?', r'do\s+a?\s*research\s+(on\s+)?',
                    r'search\s+(for|about|on)\s+', r'look\s+up\s+', r'find\s+(me\s+)?',
                    r'web\s+search\s+(for\s+)?', r'latest\s+news\s+(on\s+|about\s+)?']:
            lower = re.sub(pat, '', lower)
        return lower.strip() or prompt

    # ── Main entry point ─────────────────────────────────────────────────────
    def decompose_task(self, user_prompt: str) -> OrchestratorPlan:
        print(f"[MILES] Received: '{user_prompt}'")

        # 1. Deterministic 3D route — no LLM needed
        if self._is_3d_request(user_prompt):
            obj = self._extract_object_name(user_prompt)
            print(f"[MILES] → 3D route: '{obj}'")
            return OrchestratorPlan(
                direct_response=None,
                tasks=[{"worker_name": "3D_Generator", "prompt": obj}]
            )

        # 2. Deterministic RAG route — explicit search command only
        if self._is_rag_request(user_prompt):
            query = self._extract_rag_query(user_prompt)
            print(f"[MILES] → RAG route: '{query}'")
            return OrchestratorPlan(
                direct_response=None,
                tasks=[{"worker_name": "RAG_Search", "prompt": query}]
            )

        # 3. Everything else → Gemini direct chat (JSON mode, NO history to avoid re-planning)
        print(f"[MILES] → Direct chat")
        raw = self._call_gemini_json(user_prompt)
        if raw is None:
            return OrchestratorPlan(
                direct_response="I'm having trouble connecting right now. Please try again.",
                tasks=[]
            )
        return self._parse_response(raw, user_prompt)

    def _call_gemini_json(self, user_prompt: str) -> str | None:
        """
        Call Gemini in JSON mode WITHOUT conversation history.
        History was the root cause of re-planning: Gemini saw "conduct research on X"
        in history and applied it to unrelated follow-up questions.
        """
        for attempt in range(len(self.api_keys) + 1):
            try:
                # Fresh chat every time — no stale history contamination
                chat = self.model.start_chat(history=[])
                response = chat.send_message(
                    f"User message: {user_prompt}",
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json"
                    ),
                )
                return response.text
            except Exception as e:
                is_rate = any(x in str(e) for x in ["429", "ResourceExhausted", "QuotaExceeded"])
                if is_rate and self._rotate_key():
                    continue
                print(f"[MILES] Gemini error: {e}")
                return None
        return None

    def _parse_response(self, raw: str, original_prompt: str) -> OrchestratorPlan:
        try:
            cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
            data: Any = json.loads(cleaned)

            if not isinstance(data, dict):
                raise ValueError("Not a dict")

            direct_response = data.get("direct_response") or None
            tasks = data.get("tasks") or []

            # Guard: if direct_response is itself JSON, unwrap it
            if direct_response and direct_response.strip().startswith("{"):
                print("[MILES] WARNING: direct_response contained JSON — unwrapping")
                try:
                    inner = json.loads(direct_response)
                    direct_response = inner.get("direct_response") or "Done."
                    if not tasks:
                        tasks = inner.get("tasks") or []
                except Exception:
                    direct_response = "I processed your request."

            # Guard: strip any spurious 3D or RAG tasks from a direct-chat reply
            # (only keep tasks if there's no direct_response)
            if direct_response and tasks:
                print("[MILES] WARNING: Gemini added tasks to a direct reply — stripping spurious tasks")
                tasks = []

            return OrchestratorPlan(direct_response=direct_response, tasks=tasks)

        except Exception as exc:
            print(f"[MILES] JSON parse failed: {exc}")
            # Best-effort: return raw text as plain response
            return OrchestratorPlan(direct_response=raw.strip(), tasks=[])

    def answer_prompt(self, user_prompt: str) -> str:
        plan = self.decompose_task(user_prompt)
        return plan.direct_response or "No response generated."
