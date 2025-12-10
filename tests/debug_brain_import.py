
import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.abspath("."))

from src.orchestrator.orchestrator import get_orchestrator

print("--- DEBUG START ---")
print(f"Loading orchestrator...")
try:
    brain = get_orchestrator()
    print(f"Orchestrator Class: {brain.__class__.__name__}")
    print(f"Orchestrator Module: {brain.__class__.__module__}")
    
    print("Test 1: Decompose 'hi'")
    plan = brain.decompose_task("hi")
    print(f"Plan Direct Response: {plan.direct_response}")
    print(f"Plan Tasks: {plan.tasks}")

except Exception as e:
    print(f"CRITICAL FAILURE: {e}")
    import traceback
    traceback.print_exc()

print("--- DEBUG END ---")
