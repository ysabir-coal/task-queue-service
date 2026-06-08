"""Background task worker."""

import asyncio
import logging
import signal
import time
from typing import Any

from app.config import settings
from app.models import TaskStatus
from app.notifications import send_webhook
from app.queue import TaskQueue

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, queue: TaskQueue):
        self._queue = queue
        self._running = False

    async def start(self) -> None:
        """Start the worker loop."""
        self._running = True
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        logger.info("Worker started")

        while self._running:
            task = self._queue.dequeue()
            if task is None:
                await asyncio.sleep(1)
                continue
            await self._process_task(task)

    async def _process_task(self, task: dict) -> None:
        task_id = task["task_id"]
        logger.info("Processing task: %s (%s)", task_id, task["name"])
        start_time = time.time()

        try:
            result = await self._execute(task)
            elapsed = time.time() - start_time

            if elapsed > task["timeout_seconds"]:
                raise TimeoutError(f"Task exceeded timeout of {task['timeout_seconds']}s")

            self._queue.complete(task_id, result)
            logger.info("Task completed: %s (%.2fs)", task_id, elapsed)

            # Send webhook if configured
            if task.get("callback_url"):
                await send_webhook(
                    task["callback_url"], task_id, TaskStatus.COMPLETED.value, result=result
                )

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            logger.error("Task failed: %s (%.2fs) — %s", task_id, elapsed, error_msg)

            should_retry = self._queue.fail(task_id, error_msg)
            if not should_retry and task.get("callback_url"):
                await send_webhook(
                    task["callback_url"], task_id, TaskStatus.FAILED.value, error=error_msg
                )

    async def _execute(self, task: dict) -> dict[str, Any]:
        """Execute a task. Override in subclass for real processing."""
        # Simulate work
        await asyncio.sleep(0.1)
        return {"processed": True, "task_name": task["name"]}

    def _handle_shutdown(self, signum, frame) -> None:
        logger.info("Shutdown signal received")
        self._running = False
