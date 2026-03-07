"""Tests for the rate limiter."""

import os
import tempfile

import pytest

from bracc_telegram.rate_limiter import RateLimiter


@pytest.fixture
def tmp_db(tmp_path: object) -> str:  # noqa: ARG001
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path  # type: ignore[misc]
    os.unlink(path)


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_allows_within_limit(self, tmp_db: str) -> None:
        limiter = RateLimiter(db_path=tmp_db, limit=3)
        allowed, remaining = await limiter.check_and_increment(chat_id=123)
        assert allowed is True
        assert remaining == 2

    @pytest.mark.asyncio
    async def test_blocks_after_limit(self, tmp_db: str) -> None:
        limiter = RateLimiter(db_path=tmp_db, limit=2)
        await limiter.check_and_increment(chat_id=456)
        await limiter.check_and_increment(chat_id=456)
        allowed, remaining = await limiter.check_and_increment(chat_id=456)
        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_different_users_independent(self, tmp_db: str) -> None:
        limiter = RateLimiter(db_path=tmp_db, limit=1)
        allowed1, _ = await limiter.check_and_increment(chat_id=100)
        allowed2, _ = await limiter.check_and_increment(chat_id=200)
        assert allowed1 is True
        assert allowed2 is True

    @pytest.mark.asyncio
    async def test_get_remaining(self, tmp_db: str) -> None:
        limiter = RateLimiter(db_path=tmp_db, limit=5)
        assert await limiter.get_remaining(chat_id=789) == 5
        await limiter.check_and_increment(chat_id=789)
        assert await limiter.get_remaining(chat_id=789) == 4

    def test_days_until_reset(self) -> None:
        days = RateLimiter.days_until_reset()
        assert 0 <= days <= 31
