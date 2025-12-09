"""
Lightweight rule-based responder for trivial prompts.

This is used to keep the orchestrator/Celery pipeline focused on
heavy research or generation tasks. Greetings, small-talk, and
basic arithmetic are answered here synchronously.
"""

from __future__ import annotations

import ast
import operator
import re
from typing import Callable, Optional


GREETING_KEYWORDS = {
    "hi",
    "hello",
    "hey",
    "hola",
    "yo",
    "sup",
}


def try_simple_response(prompt: str) -> Optional[str]:
    """
    Attempt to generate a fast local response without invoking the orchestrator.

    Returns:
        A string response if the prompt is classified as trivial, otherwise None.
    """

    stripped = prompt.strip()
    normalized = stripped.lower()

    if not stripped:
        return "Please provide a prompt so I know how to assist."

    if normalized in GREETING_KEYWORDS or normalized.startswith(("hi ", "hello ", "hey ")):
        return "Hello! I'm MILES. Ask me something more substantial and I'll bring in the specialists."

    if "your name" in normalized:
        return "I'm MILES – the Multimodal Intelligent Assistant orchestrating the specialists."

    if _looks_like_math(normalized):
        try:
            return f"The answer is { _safe_eval_math(stripped) }."
        except ValueError:
            return "I tried to compute that, but the expression wasn't recognized."

    if len(stripped) <= 20 and normalized.endswith("?"):
        return "That's a quick question. Could you add more detail so I know whether to research it?"

    if len(stripped.split()) <= 3 and not normalized.endswith("?"):
        return "Could you elaborate a bit more? I want to ensure I send the right specialists."

    return None


HEAVY_KEYWORDS = {
    "research",
    "deep dive",
    "analyze",
    "analysis",
    "report",
    "whitepaper",
    "citation",
    "compare",
    "survey",
    "comprehensive",
    "study",
    "pipeline",
    "architecture",
    "implementation details",
    "evaluation",
    "benchmark",
}


def needs_deep_research(prompt: str) -> bool:
    """
    Determine whether a prompt should be routed to the full Orchestrator/worker pipeline.
    """

    normalized = prompt.lower()
    return any(keyword in normalized for keyword in HEAVY_KEYWORDS)


MATH_PATTERN = re.compile(r"^[\d\.\s\+\-\*\/\(\)]+$")


def _looks_like_math(value: str) -> bool:
    return bool(MATH_PATTERN.match(value))


_OPS: dict[type[ast.AST], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}


def _safe_eval_math(expression: str) -> float:
    """
    Safely evaluate a basic arithmetic expression using the AST.
    """

    node = ast.parse(expression, mode="eval")
    return _eval(node.body)


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Num):  # type: ignore[attr-defined]
        return node.n  # type: ignore[return-value]
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    raise ValueError("Unsupported expression")


