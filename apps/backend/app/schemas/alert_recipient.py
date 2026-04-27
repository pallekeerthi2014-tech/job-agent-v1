from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertRecipientCreate(BaseModel):
    phone_number: str
    label: str | None = None
    is_active: bool = True


class AlertRecipientUpdate(BaseModel):
    label: str | None = None
    is_active: bool | None = None


class AlertRecipientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone_number: str
    label: str | None
    is_active: bool
    created_at: datetime
