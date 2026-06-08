"""Tests for the task queue."""

import pytest

from app.models import TaskPriority, TaskStatus
from app.queue import TaskQueue


class TestTaskQueue:
    def test_submit_creates_task(self, task_queue):
        task = task_queue.submit(name="test-job", payload={"key": "value"})
        assert task["task_id"] is not None
        assert task["name"] == "test-job"
        assert task["status"] == TaskStatus.PENDING.value

    def test_get_returns_task(self, task_queue):
        task = task_queue.submit(name="test-job", payload={"x": 1})
        fetched = task_queue.get(task["task_id"])
        assert fetched is not None
        assert fetched["name"] == "test-job"
        assert fetched["payload"] == {"x": 1}

    def test_get_returns_none_for_missing(self, task_queue):
        assert task_queue.get("nonexistent-id") is None

    def test_dequeue_returns_highest_priority(self, task_queue):
        task_queue.submit(name="low", payload={}, priority=TaskPriority.LOW)
        task_queue.submit(name="high", payload={}, priority=TaskPriority.HIGH)
        task_queue.submit(name="medium", payload={}, priority=TaskPriority.MEDIUM)

        task = task_queue.dequeue()
        assert task["name"] == "high"

    def test_dequeue_sets_running_status(self, task_queue):
        task_queue.submit(name="job", payload={})
        task = task_queue.dequeue()
        assert task["status"] == TaskStatus.RUNNING.value

    def test_complete_sets_result(self, task_queue):
        task = task_queue.submit(name="job", payload={})
        task_queue.complete(task["task_id"], {"output": "done"})
        fetched = task_queue.get(task["task_id"])
        assert fetched["status"] == TaskStatus.COMPLETED.value
        assert fetched["result"] == {"output": "done"}

    def test_fail_retries_when_under_limit(self, task_queue):
        task = task_queue.submit(name="job", payload={}, max_retries=3)
        should_retry = task_queue.fail(task["task_id"], "oops")
        assert should_retry is True
        fetched = task_queue.get(task["task_id"])
        assert fetched["status"] == TaskStatus.RETRYING.value
        assert fetched["retry_count"] == 1

    def test_fail_marks_failed_when_retries_exhausted(self, task_queue):
        task = task_queue.submit(name="job", payload={}, max_retries=1)
        should_retry = task_queue.fail(task["task_id"], "fatal")
        assert should_retry is False
        fetched = task_queue.get(task["task_id"])
        assert fetched["status"] == TaskStatus.FAILED.value

    def test_delete_removes_task(self, task_queue):
        task = task_queue.submit(name="job", payload={})
        assert task_queue.delete(task["task_id"]) is True
        assert task_queue.get(task["task_id"]) is None

    def test_list_tasks_pagination(self, task_queue):
        for i in range(5):
            task_queue.submit(name=f"job-{i}", payload={})
        tasks, total = task_queue.list_tasks(page=1, page_size=2)
        assert len(tasks) == 2
        assert total == 5
