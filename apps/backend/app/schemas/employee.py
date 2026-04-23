from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr


class EmployeeBase(BaseModel):
    name: str
    email: EmailStr


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

