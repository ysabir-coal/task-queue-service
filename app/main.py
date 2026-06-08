"""FastAPI application — Task Queue Service."""

from fastapi import FastAPI, HTTPException, Query

from app.models import (
    CreateTaskRequest,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
)
from app.queue import TaskQueue

app = FastAPI(title="Task Queue Service", version="1.0.0")
queue = TaskQueue()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(request: CreateTaskRequest):
    task = queue.submit(
        name=request.name,
        payload=request.payload,
        priority=request.priority,
        callback_url=request.callback_url,
        max_retries=request.max_retries,
        timeout_seconds=request.timeout_seconds,
    )
    return _task_to_response(task)


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    task = queue.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    tasks, total = queue.list_tasks(page=page, page_size=page_size)
    return TaskListResponse(
        tasks=[_task_to_response(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str):
    deleted = queue.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


@app.post("/tasks/{task_id}/retry", response_model=TaskResponse)
async def retry_task(task_id: str):
    task = queue.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in (TaskStatus.FAILED.value, TaskStatus.COMPLETED.value):
        raise HTTPException(status_code=409, detail="Task is not in a terminal state")
    # Re-submit with same params
    new_task = queue.submit(
        name=task["name"],
        payload=task["payload"],
        priority=task["priority"],
        callback_url=task.get("callback_url"),
    )
    return _task_to_response(new_task)


def _task_to_response(task: dict) -> TaskResponse:
    return TaskResponse(
        task_id=task["task_id"],
        name=task["name"],
        status=TaskStatus(task["status"]),
        priority=task["priority"],
        payload=task["payload"],
        result=task.get("result"),
        error=task.get("error"),
        retry_count=task.get("retry_count", 0),
        created_at=task["created_at"],
        updated_at=task["updated_at"],
        completed_at=task.get("completed_at"),
    )
