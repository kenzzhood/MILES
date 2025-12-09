import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.schemas import UserRequest, OrchestratorPlan, OrchestratorTask
from src.api.endpoints import handle_interaction

async def run_verification():
    print("Starting Hybrid Orchestrator Verification...")

    # Mock Orchestrator
    mock_orchestrator = MagicMock()
    
    # Mock Celery Task
    mock_task = MagicMock()
    mock_task.delay.return_value.id = "mock_task_id_123"
    
    # Mock Worker Map
    mock_worker_map = {
        "RAG_Search": mock_task
    }

    with patch("src.api.endpoints.get_orchestrator", return_value=mock_orchestrator), \
         patch("src.api.endpoints.WORKER_MAP", mock_worker_map):

        # Test 1: Direct Answer
        print("\nTest 1: Direct Answer (Conversational)")
        mock_orchestrator.decompose_task.return_value = OrchestratorPlan(
            direct_response="Hello! How can I help?",
            tasks=[]
        )
        response = await handle_interaction(UserRequest(prompt="Hello"))
        print(f"Response: {response.direct_response}")
        print(f"Task IDs: {response.task_ids}")
        assert response.direct_response == "Hello! How can I help?"
        assert len(response.task_ids) == 0
        print("✅ Passed")

        # Test 2: Task Only
        print("\nTest 2: Task Only (Research)")
        mock_orchestrator.decompose_task.return_value = OrchestratorPlan(
            direct_response=None,
            tasks=[OrchestratorTask(worker_name="RAG_Search", prompt="Research AI")]
        )
        response = await handle_interaction(UserRequest(prompt="Research AI"))
        print(f"Response: {response.direct_response}")
        print(f"Task IDs: {response.task_ids}")
        assert response.direct_response is None
        assert len(response.task_ids) == 1
        print("✅ Passed")

        # Test 3: Hybrid (Mixed)
        print("\nTest 3: Hybrid (Chat + Research)")
        mock_orchestrator.decompose_task.return_value = OrchestratorPlan(
            direct_response="Sure, I'll look that up.",
            tasks=[OrchestratorTask(worker_name="RAG_Search", prompt="Research Quantum")]
        )
        response = await handle_interaction(UserRequest(prompt="Research Quantum"))
        print(f"Response: {response.direct_response}")
        print(f"Task IDs: {response.task_ids}")
        assert response.direct_response == "Sure, I'll look that up."
        assert len(response.task_ids) == 1
        print("✅ Passed")

if __name__ == "__main__":
    asyncio.run(run_verification())
