@echo off
echo Starting MILES System...

:: 1. Start Celery Worker (Background or Separate Window)
:: We use start /min to keep it less intrusive
echo Starting Celery Worker...
start "MILES Worker" /min celery -A src.workers.celery_app worker --loglevel=info -P solo

:: 2. Start FastAPI Server (Main Interface)
echo Starting Orchestrator API...
:: This will also trigger the SF3D Service startup via lifespan events
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

:: Pause if uvicorn exits
pause
