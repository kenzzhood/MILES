
import sys
import os

sys.path.insert(0, os.path.abspath("."))
from src.orchestrator.gemini_brain import GeminiOrchestrator

print("--- BRAIN LOGIC DEBUG ---")
brain = GeminiOrchestrator()

test_prompts = ["hi", "Hi", "hi.", "Hello", "Search for apple", "Make a donut"]

for p in test_prompts:
    print(f"\nTesting Prompt: '{p}'")
    # We want to see the logs printed by decompose_task
    try:
        # We mock the chat start to avoid hitting API if possible, 
        # but the logic comes BEFORE chat start, so we might see logs.
        # Actually, let's just let it run. It might fail on API, but we want to see [DEBUG_BRAIN] logs.
        brain.decompose_task(p)
    except Exception as e:
        print(f"Result: Exception ({e}) (Expected if API fails)")

print("--- LOGIC DEBUG COMPLETE ---")
