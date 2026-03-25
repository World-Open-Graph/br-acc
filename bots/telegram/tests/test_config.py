from __future__ import annotations

import pytest

from bracc_telegram import config


def test_get_telegram_token_requires_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        config.get_telegram_token()


def test_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRACC_API_URL", raising=False)
    monkeypatch.delenv("RATE_LIMIT_PER_MONTH", raising=False)
    monkeypatch.delenv("RATE_LIMIT_DB_PATH", raising=False)

    assert config.get_api_url() == "http://localhost:8000"
    assert config.get_rate_limit_per_month() == 10
    assert config.get_db_path() == "data/rate_limit.db"
