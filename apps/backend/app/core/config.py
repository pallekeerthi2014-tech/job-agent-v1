from __future__ import annotations

import logging
import warnings
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_INSECURE_JWT_DEFAULTS = {"change-me-in-production", "secret", "changeme", ""}
_INSECURE_PASSWORD_DEFAULTS = {"ChangeMe123!", "ThinkSuccess123!", "password", ""}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Core ──────────────────────────────────────────────────────────────────
    app_name: str = "Job Matching Operations Dashboard"
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="job_ops", alias="POSTGRES_DB")
    postgres_user: str = Field(default="job_ops", alias="POSTGRES_USER")
    postgres_password: str = Field(default="job_ops", alias="POSTGRES_PASSWORD")

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="ALLOWED_ORIGINS",
    )

    # ── Scheduler ─────────────────────────────────────────────────────────────
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    scheduler_timezone: str = Field(default="UTC", alias="SCHEDULER_TIMEZONE")
    daily_job_hour: int = Field(default=6, alias="DAILY_JOB_HOUR")
    daily_job_minute: int = Field(default=0, alias="DAILY_JOB_MINUTE")
    poll_interval_minutes: int = Field(default=15, alias="POLL_INTERVAL_MINUTES")

    # ── Job pipeline ──────────────────────────────────────────────────────────
    default_queue_limit: int = Field(default=50, alias="DEFAULT_QUEUE_LIMIT")
    fresh_job_max_age_hours: int = Field(default=168, alias="FRESH_JOB_MAX_AGE_HOURS")
    seed_sample_candidates: bool = Field(default=False, alias="SEED_SAMPLE_CANDIDATES")

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(default="change-me-in-production", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    reset_token_expire_minutes: int = Field(default=60, alias="RESET_TOKEN_EXPIRE_MINUTES")

    # ── Admin bootstrap ───────────────────────────────────────────────────────
    public_app_url: str = Field(default="http://localhost:5173", alias="PUBLIC_APP_URL")
    super_admin_email: str = Field(default="admin@thinksuccessitconsulting.com", alias="SUPER_ADMIN_EMAIL")
    super_admin_password: str = Field(default="ChangeMe123!", alias="SUPER_ADMIN_PASSWORD")
    super_admin_name: str = Field(default="Super Admin", alias="SUPER_ADMIN_NAME")
    employee_default_password: str = Field(default="ThinkSuccess123!", alias="EMPLOYEE_DEFAULT_PASSWORD")

    # ── SMTP / Email ──────────────────────────────────────────────────────────
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")

    # ── Alert thresholds ──────────────────────────────────────────────────────
    alert_min_score: float = Field(default=65.0, alias="ALERT_MIN_SCORE")

    # ── WhatsApp / Twilio ─────────────────────────────────────────────────────
    whatsapp_alerts_enabled: bool = Field(default=False, alias="WHATSAPP_ALERTS_ENABLED")
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from: str = Field(default="", alias="TWILIO_WHATSAPP_FROM")
    whatsapp_team_numbers: str = Field(default="", alias="WHATSAPP_TEAM_NUMBERS")

    # ── Email alerts ──────────────────────────────────────────────────────────
    email_alerts_enabled: bool = Field(default=False, alias="EMAIL_ALERTS_ENABLED")

    # ── AI scoring ────────────────────────────────────────────────────────────
    ai_scoring_enabled: bool = Field(default=False, alias="AI_SCORING_ENABLED")
    ai_provider: str = Field(default="openai", alias="AI_PROVIDER")
    ai_model: str = Field(default="gpt-4o-mini", alias="AI_MODEL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # ── Google OAuth ──────────────────────────────────────────────────────────
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_oauth_redirect_uri: str = Field(default="http://localhost:8000/api/v1/admin/gmail/oauth/callback", alias="GOOGLE_OAUTH_REDIRECT_URI")
    google_token_encryption_key: str = Field(default="", alias="GOOGLE_TOKEN_ENCRYPTION_KEY")
    gmail_analytics_enabled: bool = Field(default=False, alias="GMAIL_ANALYTICS_ENABLED")
    gmail_scan_interval_minutes: int = Field(default=30, alias="GMAIL_SCAN_INTERVAL_MINUTES")
    gmail_scan_lookback_days: int = Field(default=14, alias="GMAIL_SCAN_LOOKBACK_DAYS")
    gmail_calendar_lookahead_days: int = Field(default=30, alias="GMAIL_CALENDAR_LOOKAHEAD_DAYS")
    google_sheets_report_id: str = Field(default="", alias="GOOGLE_SHEETS_REPORT_ID")
    google_service_account_json: str = Field(default="", alias="GOOGLE_SERVICE_ACCOUNT_JSON")

    # ── USAJobs ───────────────────────────────────────────────────────────────
    usajobs_api_key: str = Field(default="", alias="USAJOBS_API_KEY")
    usajobs_user_agent_email: str = Field(
        default="ops@thinksuccessitconsulting.com",
        alias="USAJOBS_USER_AGENT_EMAIL",
    )

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def twilio_whatsapp_from_formatted(self) -> str:
        n = self.twilio_whatsapp_from.strip()
        return n if n.startswith("whatsapp:") else f"whatsapp:{n}" if n else ""

    @property
    def whatsapp_team_numbers_list(self) -> list[str]:
        return [
            n.strip() if n.strip().startswith("whatsapp:") else f"whatsapp:{n.strip()}"
            for n in self.whatsapp_team_numbers.split(",")
            if n.strip()
        ]

    # ── Startup validation ────────────────────────────────────────────────────
    @model_validator(mode="after")
    def _warn_insecure_defaults(self) -> "Settings":
        issues: list[str] = []

        if self.jwt_secret_key in _INSECURE_JWT_DEFAULTS:
            issues.append(
                "JWT_SECRET_KEY is still the insecure default. "
                "Set a strong random value (e.g. `openssl rand -hex 32`) before going live."
            )
        if self.super_admin_password in _INSECURE_PASSWORD_DEFAULTS:
            issues.append("SUPER_ADMIN_PASSWORD is still the insecure default. Change it in .env.")
        if self.employee_default_password in _INSECURE_PASSWORD_DEFAULTS:
            issues.append("EMPLOYEE_DEFAULT_PASSWORD is still the insecure default. Change it in .env.")
        if self.whatsapp_alerts_enabled and (
            not self.twilio_account_sid or not self.twilio_auth_token or not self.twilio_whatsapp_from
        ):
            issues.append(
                "WHATSAPP_ALERTS_ENABLED=true but Twilio credentials are incomplete. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM."
            )
        if self.email_alerts_enabled and not self.smtp_host:
            issues.append("EMAIL_ALERTS_ENABLED=true but SMTP_HOST is not set.")
        if self.ai_scoring_enabled:
            if self.ai_provider == "openai" and not self.openai_api_key:
                issues.append("AI_SCORING_ENABLED=true (openai) but OPENAI_API_KEY is not set.")
            if self.ai_provider == "anthropic" and not self.anthropic_api_key:
                issues.append("AI_SCORING_ENABLED=true (anthropic) but ANTHROPIC_API_KEY is not set.")
        if self.gmail_analytics_enabled:
            if not self.google_client_id or not self.google_client_secret:
                issues.append("GMAIL_ANALYTICS_ENABLED=true but GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET are incomplete.")
            if not self.google_token_encryption_key:
                issues.append("GMAIL_ANALYTICS_ENABLED=true but GOOGLE_TOKEN_ENCRYPTION_KEY is not set.")
        for issue in issues:
            warnings.warn(f"[config] {issue}", stacklevel=2)

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
