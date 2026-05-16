import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is missing from the environment.")
    return value


@dataclass(frozen=True)
class Settings:
    db_user: str
    db_password: str
    db_url: str
    db_name: str
    apify_client_key: str | None
    google_api_key: str | None
    nvidia_api_key: str | None
    groq_api_key: str | None
    gemini_model: str
    nvidia_llm_model: str
    groq_llm_model: str
    scheduler_user_id: str | None
    scheduler_timezone: str
    scheduler_am_hour: int
    scheduler_am_minute: int
    scheduler_pm_hour: int
    scheduler_pm_minute: int
    apify_limit_per_source: int
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_use_tls: bool
    resume_attachment_path: str
    email_signoff_name: str


load_env_file()


def _opt(key: str) -> str | None:
    v = os.getenv(key)
    if not v:
        return None
    v = v.split("#", 1)[0].strip()
    return v or None


def _int_env(*keys: str, default: int, min_val: int = 1, max_val: int = 500) -> int:
    for key in keys:
        raw = _opt(key)
        if raw is not None:
            try:
                val = int(raw)
            except ValueError as exc:
                msg = f"{key} must be an integer (Apify limitPerSource), got {raw!r}"
                raise ValueError(msg) from exc
            return max(min_val, min(max_val, val))
    return default


def _bool_env(name: str, *, default: bool) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    if not v:
        return default
    return v in {"1", "true", "yes", "on"}


def parse_scheduler_time(value: str, *, default_hour: int, default_minute: int = 0) -> tuple[int, int]:
    """
    Parse a clock time for cron scheduling.

    Supported formats (24-hour recommended):
      - HH:MM           e.g. 06:00, 18:30
      - H:MM            e.g. 6:00
      - HH:MM AM/PM     e.g. 6:00 AM, 6:00 PM
    """
    raw = (value or "").strip()
    if not raw:
        return default_hour, default_minute

    am_pm: str | None = None
    upper = raw.upper()
    if upper.endswith("AM"):
        am_pm = "AM"
        raw = raw[:-2].strip()
    elif upper.endswith("PM"):
        am_pm = "PM"
        raw = raw[:-2].strip()

    if ":" in raw:
        hour_part, minute_part = raw.split(":", 1)
    else:
        hour_part, minute_part = raw, "0"

    hour = int(hour_part.strip())
    minute = int(minute_part.strip())

    if am_pm == "AM":
        if hour == 12:
            hour = 0
    elif am_pm == "PM":
        if hour != 12:
            hour += 12

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        msg = f"Time out of range: {value!r} (use hour 0–23, minute 0–59)"
        raise ValueError(msg)

    return hour, minute


def _scheduler_time_from_env(*keys: str, default: str) -> tuple[int, int]:
    for key in keys:
        raw = _opt(key)
        if raw:
            return parse_scheduler_time(raw, default_hour=0, default_minute=0)
    return parse_scheduler_time(default, default_hour=0, default_minute=0)


_am_time = _scheduler_time_from_env("AM_Time_Harsh", default="06:00")
_pm_time = _scheduler_time_from_env("PM_time_harsh", "PM_Time_Harsh", default="18:00")

settings = Settings(
    db_user=get_required_env("DB_USER"),
    db_password=get_required_env("DB_PASSWORD"),
    db_url=get_required_env("DB_URL"),
    db_name=get_required_env("DB_NAME"),
    apify_client_key=(os.getenv("APIFY_CLIENT_KEY") or "").strip() or None,
    google_api_key=_opt("GOOGLE_API_KEY") or _opt("GEMINI_API_KEY"),
    nvidia_api_key=_opt("NVIDIA_API_KEY"),
    groq_api_key=_opt("GROQ_API_KEY"),
    gemini_model=(os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip(),
    nvidia_llm_model=(os.getenv("NVIDIA_LLM_MODEL") or "meta/llama-3.1-70b-instruct").strip(),
    groq_llm_model=(os.getenv("GROQ_LLM_MODEL") or "llama-3.3-70b-versatile").strip(),
    scheduler_user_id=_opt("SCHEDULER_USER_ID_HARSH") or _opt("SCHEDULER_USER_ID"),
    scheduler_timezone=(os.getenv("SCHEDULER_TIMEZONE") or "Asia/Kolkata").strip(),
    scheduler_am_hour=_am_time[0],
    scheduler_am_minute=_am_time[1],
    scheduler_pm_hour=_pm_time[0],
    scheduler_pm_minute=_pm_time[1],
    apify_limit_per_source=_int_env(
        "LIMIT_PER_SOURCE_HARSH",
        "LIMIT_PER_SOURCE",
        default=10,
        min_val=1,
        max_val=500,
    ),
    smtp_host=_opt("SMTP_HOST"),
    smtp_port=int((os.getenv("SMTP_PORT") or "587").strip()),
    smtp_username=_opt("SMTP_USER_HARSH") or _opt("SMTP_USER") or _opt("SMTP_USERNAME"),
    smtp_password=_opt("SMTP_PASSWORD_HARSH") or _opt("SMTP_PASSWORD"),
    smtp_use_tls=_bool_env("SMTP_USE_TLS", default=True),
    resume_attachment_path=(
        os.getenv("RESUME_ATTACHMENT_PATH") or r"d:\Downloads\Harsh-Gupta-Resume.pdf"
    ).strip(),
    email_signoff_name=(
        os.getenv("EMAIL_SIGNOFF_NAME_HARSH") or os.getenv("EMAIL_SIGNOFF_NAME") or "Harsh Gupta"
    ).strip(),
)
