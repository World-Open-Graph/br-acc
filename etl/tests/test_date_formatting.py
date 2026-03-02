from __future__ import annotations

import pytest

from bracc_etl.transforms.date_formatting import parse_date


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("15/01/2020", "2020-01-15"),
        ("2020-01-15", "2020-01-15"),
        ("20200115", "2020-01-15"),
        ("31/12/2024 14:30:00", "2024-12-31"),
        ("", ""),
        ("  ", ""),
        ("invalid", ""),
        ("01/01/2000", "2000-01-01"),
    ],
)
def test_parse_date(raw: str, expected: str) -> None:
    assert parse_date(raw) == expected
