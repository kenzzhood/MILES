import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import config
from src.orchestrator.gemini_orchestrator import GeminiOrchestrator

def test_routing():
    print("Testing Orchestrator Routing for 'Make the handle red'...")
    orch = GeminiOrchestrator(api_key=config.GEMINI_API_KEY, model_name=config.GEMINI_MODEL_NAME)
    
    prompt = "Make the handle red"
    plan = orch.decompose_task(prompt)
    
    print("\nPlan:")
    print(plan)
    
    if plan.tasks:
        worker = plan.tasks[0].worker_name
        print(f"\nAssigned Worker: {worker}")
        if worker == "3D_Generator":
            print("PASS: Correctly assigned to 3D_Generator")
        else:
            print(f"FAIL: Assigned to {worker} (expected 3D_Generator)")
    else:
        print("FAIL: No tasks assigned.")

if __name__ == "__main__":
    test_routing()
