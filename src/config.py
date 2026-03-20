import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class SmtpSettings:
    host: str | None
    port: int
    user: str | None
    password: str | None
    mail_from: str | None
    timeout_seconds: int


@dataclass(frozen=True)
class Settings:
    database_url: str
    default_timezone: str = "America/Bogota"
    smtp: SmtpSettings | None = None


def _clean_env_value(value: str) -> str:
    stripped = value.strip()
    if (stripped.startswith('"') and stripped.endswith('"')) or (
        stripped.startswith("'") and stripped.endswith("'")
    ):
        return stripped[1:-1]
    return stripped


def _read_env(name: str) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    return _clean_env_value(raw)


def get_settings() -> Settings:
    load_dotenv()

    # Prioriza la URL pooler (6543) para entornos donde 5432 no esta disponible.
    database_url = _read_env("DATABASE_URL")
    direct_url = _read_env("DIRECT_URL")
    db_url = database_url or direct_url

    if not db_url:
        raise ValueError("No existe DATABASE_URL o DIRECT_URL en el entorno")

    default_timezone = _read_env("DEFAULT_TIMEZONE") or "America/Bogota"

    smtp_host = _read_env("SMTP_HOST")
    smtp_port_raw = _read_env("SMTP_PORT")
    smtp_user = _read_env("SMTP_USER")
    smtp_pass = _read_env("SMTP_PASS")
    mail_from = _read_env("MAIL_FROM") or smtp_user
    smtp_timeout_raw = _read_env("SMTP_TIMEOUT_SECONDS")

    smtp_settings: SmtpSettings | None = None
    if smtp_host:
        smtp_settings = SmtpSettings(
            host=smtp_host,
            port=int(smtp_port_raw or "587"),
            user=smtp_user,
            password=smtp_pass,
            mail_from=mail_from,
            timeout_seconds=int(smtp_timeout_raw or "10"),
        )

    return Settings(
        database_url=db_url,
        default_timezone=default_timezone,
        smtp=smtp_settings,
    )
