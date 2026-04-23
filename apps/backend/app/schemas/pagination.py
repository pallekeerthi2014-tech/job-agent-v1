from __future__ import annotations

from pydantic import BaseModel


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int
