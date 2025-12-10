
import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.abspath("."))

from src import config
from src.orchestrator.gemini_brain import GeminiOrchestrator

def debug_orchestrator():
    print("\nXXX DEBUG START XXX")
    print(f"Config Keys: {config.GEMINI_API_KEYS}")
    
    try:
        brain = GeminiOrchestrator()
        print(f"Initialized Brain with keys: {brain.api_keys}")
    except Exception as e:
        print(f"Failed to initialize brain: {e}")
        return

    prompt = "hi"
    print(f"\n--- Testing Prompt: '{prompt}' ---")
    
    # We want to see the internal prints from gemini_brain.py
    # But checking the result tells us which path it took.
    
    try:
        plan = brain.decompose_task(prompt)
        print("\n--- Result ---")
        print(f"Direct Response: {plan.direct_response}")
        print(f"Tasks: {plan.tasks}")
        
        if "Rate Limit Reached" in plan.direct_response:
             print("\n!!! FAILURE: Still getting Rate Limit message !!!")
        else:
             print("\nSUCCESS: Got valid response.")
             
    except Exception as e:
        print(f"\nCRITICAL ERROR during decompose_task: {e}")

if __name__ == "__main__":
    debug_orchestrator()
