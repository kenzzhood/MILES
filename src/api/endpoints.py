"""
FastAPI Endpoints - The "Nervous System"

This is the main entry point for all user interactions.
It implements the "non-blocking" logic of the MILES architecture.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, AsyncGenerator, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ..core.schemas import OrchestratorPlan, TaskDispatchResponse, UserRequest
from ..orchestrator.orchestrator import get_orchestrator
from ..workers.celery_app import celery_app
from ..workers.tasks_3d_generation import generate_3d_model
from ..workers.tasks_web_research import perform_web_research

router = APIRouter()

# This maps the worker names from the LLM plan to the
# actual Celery task functions.
WORKER_MAP: Dict[str, Any] = {
    "3D_Generator": generate_3d_model,
    "RAG_Search": perform_web_research,
    # "Hologram_Manipulator": ... (we would add this later)
}


@router.post("/interact", response_model=TaskDispatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def handle_interaction(request: UserRequest) -> TaskDispatchResponse:
    """
    The main interaction endpoint for MILES.

    1.  Receives the user's prompt.
    2.  Asks the Orchestrator "brain" to process it.
    3.  If the brain assigns tasks, dispatches them to Celery.
    4.  Returns the brain's direct response (if any) and task IDs (if any).
    """

    try:
        # 1. Get the current "brain" (Gemini or Ollama)
        print(f"[DEBUG_ENDPOINT] Received request: '{request.prompt}'")
        orchestrator = get_orchestrator()
        print(f"[DEBUG_ENDPOINT] Brain Type: {type(orchestrator)}")

        # 2. Ask the brain to process the request (Hybrid Decision)
        plan = orchestrator.decompose_task(request.prompt)
        print(f"[DEBUG_ENDPOINT] Plan Generated: {plan}")

        if not plan.tasks and not plan.direct_response:
            raise HTTPException(status_code=400, detail="Orchestrator could not generate a valid response.")

        # 3. Dispatch tasks to the queue (if any)
        task_ids = []
        for task in plan.tasks:
            worker_function = WORKER_MAP.get(task.worker_name)
            if worker_function is None:
                print(f"Warning: Orchestrator requested unknown worker: {task.worker_name}")
                continue

            # .delay() is the Celery command to run this "asynchronously"
            task_result = worker_function.delay(task.prompt)
            task_ids.append(task_result.id)

        # 4. Return the response
        # If we have tasks, it's a 202 Accepted (which is the default status code).
        # If we ONLY have a direct response, we might want to consider a 200 OK,
        # but for simplicity/consistency of the endpoint, 202 is fine, or we can just return.
        
        message = "Request processed."
        if task_ids:
            message = "Tasks accepted and are being processed."
        elif plan.direct_response:
            message = "Responded directly."

        return TaskDispatchResponse(
            message=message,
            task_ids=task_ids,
            plan=plan,
            direct_response=plan.direct_response,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tasks/{task_id}", summary="Check task status")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Retrieve the latest status/result for a Celery worker task.
    """

    result = AsyncResult(task_id, app=celery_app)
    return _serialize_task(result)


@router.get("/stream/{task_id}", summary="Stream task progress")
async def stream_task(task_id: str) -> StreamingResponse:
    """
    Server-Sent Events (SSE) endpoint that pushes task progress/results
    to the client without requiring explicit polling.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        result = AsyncResult(task_id, app=celery_app)
        last_state = ""

        while not result.ready():
            if result.status != last_state:
                payload = json.dumps({"task_id": task_id, "status": result.status})
                yield f"data: {payload}\n\n"
                last_state = result.status
            await asyncio.sleep(1)

        payload = json.dumps(
            {
                "task_id": task_id,
                "status": result.status,
                "result": result.result,
            }
        )
        yield f"data: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _serialize_task(result: AsyncResult) -> Dict[str, Any]:
    """
    Convert a Celery AsyncResult into a JSON-serializable dict.
    """

    response: Dict[str, Any] = {
        "task_id": result.id,
        "status": result.status,
        "successful": result.successful(),
    }

    if result.ready():
        response["result"] = result.result

    return response

