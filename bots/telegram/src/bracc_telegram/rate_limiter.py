"""Per-user rate limiter backed by SQLite."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from bracc_telegram.config import get_db_path, get_rate_limit_per_month

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS usage (
    chat_id  INTEGER NOT NULL,
    month    TEXT    NOT NULL,
    count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, month)
);
"""


def _current_month() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m")


def _days_until_month_end() -> int:
    now = datetime.now(tz=UTC)
    if now.month == 12:
        next_month_start = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month_start = now.replace(month=now.month + 1, day=1)
    return (next_month_start - now).days


class RateLimiter:
    """Track per-user monthly query counts in a local SQLite file."""

    def __init__(self, db_path: str | None = None, limit: int | None = None) -> None:
        self._db_path = db_path or get_db_path()
        self._limit = limit if limit is not None else get_rate_limit_per_month()
        self._initialised = False

    async def _ensure_db(self) -> aiosqlite.Connection:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(self._db_path)
        if not self._initialised:
            await db.execute(_CREATE_TABLE)
            await db.commit()
            self._initialised = True
        return db

    async def check_and_increment(self, chat_id: int) -> tuple[bool, int]:
        """Check if the user can make a query and increment if allowed.

        Returns ``(allowed, remaining)`` where *remaining* is the number
        of queries left this month (or 0 if exceeded).
        """
        month = _current_month()
        db = await self._ensure_db()
        try:
            cursor = await db.execute(
                "SELECT count FROM usage WHERE chat_id = ? AND month = ?",
                (chat_id, month),
            )
            row = await cursor.fetchone()
            current = row[0] if row else 0

            if current >= self._limit:
                return False, 0

            if row:
                await db.execute(
                    "UPDATE usage SET count = count + 1 WHERE chat_id = ? AND month = ?",
                    (chat_id, month),
                )
            else:
                await db.execute(
                    "INSERT INTO usage (chat_id, month, count) VALUES (?, ?, 1)",
                    (chat_id, month),
                )
            await db.commit()
            remaining = self._limit - current - 1
            return True, remaining
        finally:
            await db.close()

    async def get_remaining(self, chat_id: int) -> int:
        """Return how many queries the user has left this month."""
        month = _current_month()
        db = await self._ensure_db()
        try:
            cursor = await db.execute(
                "SELECT count FROM usage WHERE chat_id = ? AND month = ?",
                (chat_id, month),
            )
            row = await cursor.fetchone()
            current = row[0] if row else 0
            return max(0, self._limit - current)
        finally:
            await db.close()

    @staticmethod
    def days_until_reset() -> int:
        """Return how many days until the monthly limit resets."""
        return _days_until_month_end()
