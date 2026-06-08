"""Application configuration."""

import os
from pydantic import BaseModel


class Settings(BaseModel):
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    task_timeout_seconds: int = int(os.getenv("TASK_TIMEOUT", "300"))
    notification_timeout: int = int(os.getenv("NOTIFICATION_TIMEOUT", "10"))


settings = Settings()
