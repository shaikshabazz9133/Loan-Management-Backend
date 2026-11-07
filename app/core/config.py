"""Settings: defaults below, overridden by environment variables / .env (env always wins).

Secrets and connection strings come from the environment only. Business rules here are the
defaults; managers can change them at runtime via PUT /config (stored in MongoDB).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

AUTH: dict[str, Any] = {
    "access_token_ttl_minutes": 15,
    "refresh_token_ttl_days": 7,
    "otp_ttl_seconds": 300,
    "otp_max_attempts": 5,
    "password_min_length": 8,
    "lockout_after_failed_logins": 5,
    "lockout_minutes": 15,
}

BUSINESS_RULES: dict[str, Any] = {
    "assignment_radius_km": 2,
    "min_credit_score": 650,
    "max_foir": 0.5,  # EMI must be <= 50% of monthly income
    "interest_rate_pa": 12.0,
    "tenures_months": [6, 12, 18, 24, 36, 48, 60, 72, 84],
    "loan_amount": {"min": 10000, "max": 5000000},
    "applicant_age": {"min": 21, "max": 60},
    "loan_purposes": ["Personal", "Home renovation", "Education", "Medical", "Business", "Vehicle", "Wedding",
                      "Debt consolidation"],
    "employment_types": ["Salaried", "Self-employed", "Business owner", "Freelancer", "Retired"],
}

DOCUMENTS: dict[str, Any] = {
    "max_size_mb": 5,
    "allowed_mime_types": ["image/jpeg", "image/png", "image/webp", "application/pdf"],
    "presigned_url_ttl_seconds": 300,
    "required": ["pan", "aadhaar", "bank", "address"],
    "required_if_salaried": ["salary"],
}

DISBURSEMENT: dict[str, Any] = {
    "modes": ["IMPS", "NEFT", "RTGS"],
    "imps_max_amount": 500000,
    "rtgs_min_amount": 200000,
}

PAGINATION: dict[str, int] = {"default_page_size": 20, "max_page_size": 100}

RATE_LIMITS: dict[str, str] = {  # per client IP / user (slowapi + Redis)
    "default": "120/minute",
    "login": "10/minute",
    "otp_send": "3/minute",
    "uploads": "30/minute",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # app
    app_env: str = "development"
    app_name: str = "LendWise Loan Management API"
    api_prefix: str = "/api/v1"
    timezone: str = "Asia/Kolkata"
    docs_enabled: bool = True  # set DOCS_ENABLED=false in production
    log_level: str = "DEBUG"
    log_json: bool = False
    aadhaar_demo_mode: bool = False  # accept any 12-digit Aadhaar; never in production
    use_sandbox_integrations: bool = True  # credit bureau / KYC / payouts return simulated responses

    # secrets & connections
    secret_key: str
    field_encryption_key: str = ""
    mongodb_uri: str = "mongodb://localhost:27017/?replicaSet=rs0"
    mongodb_db: str = "lendwise"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str | None = None
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "lendwise-documents"
    s3_region: str = "ap-south-1"
    cors_origins: str = "http://localhost:5173"
    sentry_dsn: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
