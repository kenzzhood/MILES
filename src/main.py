"""
Main application file for the MILES project.
This file starts the FastAPI server.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager
from src.api import endpoints as api_router
from src.api import hologram_websocket

from src.services.sf3d_service import sf3d_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[MILES] Starting System v2.0 (STRICT CHAT MODE)...")
    sf3d_service.start_service()
    yield
    # Shutdown
    print("[MILES] Shutting Down...")
    sf3d_service.stop_service()

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

# Create the main FastAPI application
app = FastAPI(
    title="MILES Research Project API",
    description="API for the MILES Multimodal Intelligent Assistant.",
    version="1.0.0",
    lifespan=lifespan,
)

# Include the API router
app.include_router(api_router.router, prefix="/api/v1")
app.include_router(hologram_websocket.router)

if WEB_DIR.exists():
    app.mount("/ui", StaticFiles(directory=WEB_DIR, html=True), name="ui")

MODELS_DIR = BASE_DIR.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)
app.mount("/models", StaticFiles(directory=MODELS_DIR), name="models")


@app.get("/", summary="Root endpoint", description="Simple health check endpoint.")
async def root() -> dict[str, str]:
    """
    Health-check endpoint confirming that the Orchestrator is running.
    """

    return {"message": "MILES Orchestrator is running."}


@app.get("/playground", include_in_schema=False, summary="Chat UI")
async def playground() -> RedirectResponse:
    """
    Convenience route that redirects to the static chat UI.
    """

    return RedirectResponse(url="/ui/")


# To run the app:
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload

