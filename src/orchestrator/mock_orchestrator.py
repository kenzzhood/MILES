"""
Mock (Rule-Based) Orchestrator for local demos.

This lightweight brain allows researchers to run the full
Orchestrator-Worker pipeline without relying on external LLM APIs.
It demonstrates the task-decomposition flow using simple heuristics.
"""

from __future__ import annotations

from typing import List

from ..core.schemas import OrchestratorPlan, OrchestratorTask
from .orchestrator import OrchestratorBase


class MockOrchestrator(OrchestratorBase):
    """
    Deterministic, rule-based orchestrator used for demos and tests.

    The implementation looks for intent keywords and maps them to the
    available specialist workers.
    """

    def decompose_task(self, user_prompt: str) -> OrchestratorPlan:
        """
        Generate a simple orchestration plan without calling an external LLM.
        """

        tasks: List[OrchestratorTask] = []
        lowered = user_prompt.lower()

        if any(keyword in lowered for keyword in ["research", "explain", "find", "compare"]):
            tasks.append(
                OrchestratorTask(
                    worker_name="RAG_Search",
                    prompt=user_prompt,
                )
            )

        if any(keyword in lowered for keyword in ["hologram", "gesture", "rotate"]):
            tasks.append(
                OrchestratorTask(
                    worker_name="Hologram_Manipulator",
                    prompt="Simulate hologram command pipeline (future work).",
                )
            )

        if not tasks:
            tasks.append(
                OrchestratorTask(
                    worker_name="RAG_Search",
                    prompt=user_prompt,
                )
            )

        return OrchestratorPlan(tasks=tasks)

