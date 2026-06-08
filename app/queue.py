"""Redis-backed task queue."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis

from app.config import settings
from app.models import TaskPriority, TaskStatus


class TaskQueue:
    def __init__(self, redis_url: Optional[str] = None):
        self._redis = redis.from_url(redis_url or settings.redis_url, decode_responses=True)
        self._queue_key = "task_queue"
        self._tasks_prefix = "task:"

    def submit(
        self,
        name: str,
        payload: dict,
        priority: TaskPriority = TaskPriority.MEDIUM,
        callback_url: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ) -> dict:
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        task = {
            "task_id": task_id,
            "name": name,
            "status": TaskStatus.PENDING.value,
            "priority": priority.value,
            "payload": json.dumps(payload),
            "result": None,
            "error": None,
            "retry_count": 0,
            "max_retries": max_retries if max_retries is not None else settings.max_retries,
            "timeout_seconds": timeout_seconds or settings.task_timeout_seconds,
            "callback_url": callback_url,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }
        self._redis.hset(f"{self._tasks_prefix}{task_id}", mapping=task)
        self._redis.zadd(self._queue_key, {task_id: priority.value})
        return task

    def get(self, task_id: str) -> Optional[dict]:
        data = self._redis.hgetall(f"{self._tasks_prefix}{task_id}")
        if not data:
            return None
        data["payload"] = json.loads(data["payload"]) if data.get("payload") else {}
        if data.get("result"):
            data["result"] = json.loads(data["result"])
        data["priority"] = int(data["priority"])
        data["retry_count"] = int(data["retry_count"])
        data["max_retries"] = int(data["max_retries"])
        data["timeout_seconds"] = int(data["timeout_seconds"])
        return data

    def list_tasks(self, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        all_ids = self._redis.zrevrange(self._queue_key, 0, -1)
        total = len(all_ids)
        start = (page - 1) * page_size
        end = start + page_size
        page_ids = all_ids[start:end]
        tasks = []
        for task_id in page_ids:
            task = self.get(task_id)
            if task:
                tasks.append(task)
        return tasks, total

    def dequeue(self) -> Optional[dict]:
        """Pop highest-priority task from the queue."""
        result = self._redis.zpopmax(self._queue_key, count=1)
        if not result:
            return None
        task_id, _score = result[0]
        task = self.get(task_id)
        if task:
            self._update_status(task_id, TaskStatus.RUNNING)
        return task

    def complete(self, task_id: str, result: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._redis.hset(
            f"{self._tasks_prefix}{task_id}",
            mapping={
                "status": TaskStatus.COMPLETED.value,
                "result": json.dumps(result),
                "updated_at": now,
                "completed_at": now,
            },
        )

    def fail(self, task_id: str, error: str) -> bool:
        """Mark task as failed. Returns True if it should be retried."""
        task = self.get(task_id)
        if not task:
            return False
        retry_count = task["retry_count"] + 1
        max_retries = task["max_retries"]
        if retry_count < max_retries:
            now = datetime.now(timezone.utc).isoformat()
            self._redis.hset(
                f"{self._tasks_prefix}{task_id}",
                mapping={
                    "status": TaskStatus.RETRYING.value,
                    "retry_count": str(retry_count),
                    "error": error,
                    "updated_at": now,
                },
            )
            self._redis.zadd(self._queue_key, {task_id: task["priority"]})
            return True
        else:
            now = datetime.now(timezone.utc).isoformat()
            self._redis.hset(
                f"{self._tasks_prefix}{task_id}",
                mapping={
                    "status": TaskStatus.FAILED.value,
                    "retry_count": str(retry_count),
                    "error": error,
                    "updated_at": now,
                    "completed_at": now,
                },
            )
            return False

    def delete(self, task_id: str) -> bool:
        removed = self._redis.delete(f"{self._tasks_prefix}{task_id}")
        self._redis.zrem(self._queue_key, task_id)
        return removed > 0

    def _update_status(self, task_id: str, status: TaskStatus) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._redis.hset(
            f"{self._tasks_prefix}{task_id}",
            mapping={"status": status.value, "updated_at": now},
        )
