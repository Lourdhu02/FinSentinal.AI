from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class User(BaseModel):
    id: int | None = None
    username: str
    password_hash: str
    role: Literal["admin", "user"] = "user"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
