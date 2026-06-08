"""Tests for the FastAPI endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCreateTask:
    def test_create_task_returns_201(self, client):
        response = client.post("/tasks", json={"name": "my-task", "payload": {"a": 1}})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "my-task"
        assert data["status"] == "pending"
        assert "task_id" in data

    def test_create_task_empty_name_fails(self, client):
        response = client.post("/tasks", json={"name": "", "payload": {}})
        assert response.status_code == 422


class TestGetTask:
    def test_get_nonexistent_returns_404(self, client):
        response = client.get("/tasks/does-not-exist")
        assert response.status_code == 404
