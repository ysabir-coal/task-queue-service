"""Shared test fixtures."""

import pytest
import fakeredis

from app.queue import TaskQueue


@pytest.fixture
def redis_client():
    """Provide a fake Redis client for testing."""
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def task_queue(redis_client, monkeypatch):
    """Provide a TaskQueue backed by fake Redis."""
    q = TaskQueue.__new__(TaskQueue)
    q._redis = redis_client
    q._queue_key = "task_queue"
    q._tasks_prefix = "task:"
    return q
