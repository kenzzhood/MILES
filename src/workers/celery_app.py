"""
Celery Configuration - The "Task Queue"

This file sets up the Celery application, which connects to our
Redis server. This is the "to-do list" that the Orchestrator
puts tasks on, and the Workers pick tasks up from.
"""

from __future__ import annotations

from celery import Celery

from .. import config

# Initialize Celery
celery_app = Celery(
    "miles_workers",
    broker=config.REDIS_BROKER_URL,
    backend=config.REDIS_BACKEND_URL,
    include=[
        "src.workers.tasks_3d_generation",
        "src.workers.tasks_web_research",
    ],
)

# Optional Celery configuration
celery_app.conf.update(
    task_track_started=True,
)

