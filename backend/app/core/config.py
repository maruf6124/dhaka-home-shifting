"""App settings, read from environment variables / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Dhaka Home Shifting API"
    environment: str = "development"  # development | production | test

    # Database. MySQL in production, e.g.
    # mysql+aiomysql://user:pass@host:3306/dbname?charset=utf8mb4
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    db_pool_size: int = 5
    db_ssl: bool = False  # set true for TiDB Cloud / Aiven

    # Security
    jwt_secret: str = "change-me-in-production"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    trusted_device_days: int = 90
    otp_pepper: str = "change-me-too"
    job_secret: str = "change-me-job-secret"

    # Cookies. For Vercel (frontend) + Render (backend) on different domains use
    # cookie_secure=true and cookie_samesite="none".
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None

    # CORS: comma separated list of allowed frontend origins
    cors_origins: str = "http://localhost:3000"

    # Email. Production uses the Brevo HTTP API (Render's free plan blocks SMTP
    # ports). If brevo_api_key is empty, Gmail SMTP is used when smtp_user is set,
    # otherwise emails are printed to the console (handy for local development).
    brevo_api_key: str = ""
    email_from: str = ""  # sender address (must be verified in Brevo)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from_name: str = "Dhaka Home Shifting"
    frontend_url: str = "http://localhost:3000"

    # Cloudinary. If empty, uploads are saved in ./uploads (dev only).
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    local_upload_dir: str = "uploads"
    public_base_url: str = "http://localhost:8000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def use_cloudinary(self) -> bool:
        return bool(self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
