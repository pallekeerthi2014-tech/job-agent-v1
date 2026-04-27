from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Job Matching Operations Dashboard"
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="job_ops", alias="POSTGRES_DB")
    postgres_user: str = Field(default="job_ops", alias="POSTGRES_USER")
    postgres_password: str = Field(default="job_ops", alias="POSTGRES_PASSWORD")
    allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="ALLOWED_ORIGINS",
    )
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    scheduler_timezone: str = Field(default="UTC", alias="SCHEDULER_TIMEZONE")
    daily_job_hour: int = Field(default=6, alias="DAILY_JOB_HOUR")
    daily_job_minute: int = Field(default=0, alias="DAILY_JOB_MINUTE")
    default_queue_limit: int = Field(default=50, alias="DEFAULT_QUEUE_LIMIT")
    fresh_job_max_age_hours: int = Field(default=48, alias="FRESH_JOB_MAX_AGE_HOURS")
    jwt_secret_key: str = Field(default="change-me-in-production", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    reset_token_expire_minutes: int = Field(default=60, alias="RESET_TOKEN_EXPIRE_MINUTES")
    public_app_url: str = Field(default="http://localhost:5173", alias="PUBLIC_APP_URL")
    super_admin_email: str = Field(default="admin@thinksuccessitconsulting.com", alias="SUPER_ADMIN_EMAIL")
    super_admin_password: str = Field(default="ChangeMe123!", alias="SUPER_ADMIN_PASSWORD")
    super_admin_name: str = Field(default="Super Admin", alias="SUPER_ADMIN_NAME")
    employee_default_password: str = Field(default="ThinkSuccess123!", alias="EMPLOYEE_DEFAULT_PASSWORD")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    seed_sample_candidates: bool = Field(default=False, alias="SEED_SAMPLE_CANDIDATES")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
