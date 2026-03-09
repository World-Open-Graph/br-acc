"""Bot configuration loaded from environment variables."""

from __future__ import annotations

import os


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        msg = f"Required environment variable {name} is not set"
        raise RuntimeError(msg)
    return value


def get_telegram_token() -> str:
    """Return the Telegram bot token (required)."""
    return _require_env("TELEGRAM_BOT_TOKEN")


def get_api_url() -> str:
    """Return the BR-ACC API base URL."""
    return os.environ.get("BRACC_API_URL", "http://localhost:8000")


def get_rate_limit_per_month() -> int:
    """Return the maximum number of queries per user per month."""
    return int(os.environ.get("RATE_LIMIT_PER_MONTH", "10"))


def get_db_path() -> str:
    """Return the path to the SQLite rate-limit database."""
    return os.environ.get("RATE_LIMIT_DB_PATH", "data/rate_limit.db")
