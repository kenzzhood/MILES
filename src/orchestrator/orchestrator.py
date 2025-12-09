"""
Orchestrator Factory - The "Swappable Brain"

This module contains the abstract base class for all orchestrators
and the factory function (`get_orchestrator`) that selects the
correct "brain" (e.g., Gemini or Ollama) based on the `config.py` file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .. import config
from ..core.schemas import OrchestratorPlan


class OrchestratorBase(ABC):
    """
    Abstract Base Class for all Orchestrator models.

    This ensures that any "brain" we swap in has the same
    core `decompose_task` method.
    """

    @abstractmethod
    def decompose_task(self, user_prompt: str) -> OrchestratorPlan:
        """
        Takes a complex user prompt and decomposes it into a structured
        plan of sub-tasks for the specialist workers.

        This method implements the core Chain-of-Thought (CoT) reasoning
        of the MILES system.
        """

    @abstractmethod
    def answer_prompt(self, user_prompt: str) -> str:
        """
        Provide a direct, synchronous answer without dispatching workers.
        """


def get_orchestrator() -> OrchestratorBase:
    """
    Factory function to get the currently active orchestrator.

    This function reads the `BRAIN_MODE` from `config.py` and
    returns the corresponding orchestrator instance. This allows the
    rest of the application to be completely ignorant of *which*
    model is actually running.

    Returns:
        OrchestratorBase: Concrete orchestrator instance configured for the environment.
    """

    if config.BRAIN_MODE == "GEMINI":
        from .gemini_orchestrator import GeminiOrchestrator

        if config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_GOES_HERE":
            raise ValueError("Please set your GEMINI_API_KEY in src/config.py")

        return GeminiOrchestrator(
            api_key=config.GEMINI_API_KEY, model_name=config.GEMINI_MODEL_NAME
        )

    if config.BRAIN_MODE == "LOCAL":
        from .ollama_orchestrator import OllamaOrchestrator

        return OllamaOrchestrator(model_name=config.LOCAL_MODEL_NAME)

    if config.BRAIN_MODE == "DEMO":
        from .mock_orchestrator import MockOrchestrator

        return MockOrchestrator()

    raise ValueError(f"Unknown BRAIN_MODE in config.py: {config.BRAIN_MODE}")

