from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def generate_key() -> str:
    return Fernet.generate_key().decode("utf-8")


def _fernet() -> Fernet:
    if not settings.google_token_encryption_key:
        raise RuntimeError("GOOGLE_TOKEN_ENCRYPTION_KEY is required for Gmail analytics token storage")
    return Fernet(settings.google_token_encryption_key.encode("utf-8"))


def encrypt_token(token: str | None) -> str | None:
    if not token:
        return None
    return _fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Stored Google OAuth token could not be decrypted") from exc
