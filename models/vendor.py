from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Vendor(BaseModel):
    name: str
    tax_id: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
