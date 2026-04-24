from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def smtp_enabled() -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def send_password_reset_email(*, recipient_email: str, recipient_name: str, reset_url: str) -> None:
    if not smtp_enabled():
        raise RuntimeError("SMTP is not configured")

    message = EmailMessage()
    message["Subject"] = "Reset your Think Success dashboard password"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient_email
    message.set_content(
        (
            f"Hello {recipient_name},\n\n"
            "We received a password reset request for your Think Success dashboard account.\n"
            f"Use this link to reset your password: {reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        )
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
