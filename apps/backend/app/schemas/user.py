from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


RoleType = Literal["super_admin", "employee", "candidate"]


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: RoleType = "employee"
    is_active: bool = True
    employee_id: int | None = None
    candidate_id: int | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    role: RoleType | None = None
    is_active: bool | None = None
    employee_id: int | None = None
    candidate_id: int | None = None
    password: str | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_login_at: datetime | None = None


# ── Candidate self-registration ───────────────────────────────────────────────

class CandidateSelfRegister(BaseModel):
    """Payload for candidate self-registration via the portal."""
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    location: str | None = None
    work_authorization: str | None = None
    years_experience: int | None = None


class CandidateProfileUpdate(BaseModel):
    """What a candidate can update about themselves."""
    phone: str | None = None
    location: str | None = None
    work_authorization: str | None = None
    years_experience: int | None = None
    salary_min: int | None = None
    salary_unit: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    delivery: Literal["email", "preview"]
    reset_token: str | None = None
    reset_url: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


# ── Google OAuth ──────────────────────────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    """Frontend sends the Google credential (ID token) from Google Identity Services."""
    credential: str
