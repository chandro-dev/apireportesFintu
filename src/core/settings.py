from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_GEMINI_MODELS = [
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    api_version: str
    database_url: str | None
    direct_url: str | None
    default_timezone: str
    gemini_api_key: str | None
    gemini_model: str
    gemini_models: list[str]
    gemini_max_output_tokens: int
    reports_service_url: str | None
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_password: str | None
    mail_from: str | None
    smtp_timeout_seconds: int


def _read_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    cleaned = value.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        return cleaned[1:-1]
    return cleaned


def _read_int_env(name: str, default: int) -> int:
    value = _read_env(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un entero") from exc


def _read_csv_env(name: str) -> list[str]:
    raw = _read_env(name)
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def load_settings() -> Settings:
    load_dotenv()

    smtp_password = _read_env("SMTP_PASS") or _read_env("SMTP_PASSWORD")

    gemini_model = _read_env("GEMINI_MODEL", "gemini-2.5-flash") or "gemini-2.5-flash"
    configured_models = _read_csv_env("GEMINI_MODELS")
    gemini_models = _dedupe_keep_order(
        [gemini_model, *configured_models, *DEFAULT_GEMINI_MODELS]
    )

    return Settings(
        app_name=_read_env("APP_NAME", "fintu-backend-core") or "fintu-backend-core",
        app_env=_read_env("APP_ENV", "development") or "development",
        api_version=_read_env("API_VERSION", "v1") or "v1",
        database_url=_read_env("DATABASE_URL"),
        direct_url=_read_env("DIRECT_URL"),
        default_timezone=_read_env("DEFAULT_TIMEZONE", "America/Bogota") or "America/Bogota",
        gemini_api_key=_read_env("GEMINI_API_KEY"),
        gemini_model=gemini_model,
        gemini_models=gemini_models,
        gemini_max_output_tokens=_read_int_env("GEMINI_MAX_OUTPUT_TOKENS", 220),
        reports_service_url=_read_env("REPORTS_SERVICE_URL"),
        smtp_host=_read_env("SMTP_HOST"),
        smtp_port=_read_int_env("SMTP_PORT", 587),
        smtp_user=_read_env("SMTP_USER"),
        smtp_password=smtp_password,
        mail_from=_read_env("MAIL_FROM"),
        smtp_timeout_seconds=_read_int_env("SMTP_TIMEOUT_SECONDS", 10),
    )
