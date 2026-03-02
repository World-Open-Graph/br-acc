import logging

import pandas as pd

logger = logging.getLogger(__name__)


def parse_date(value: str) -> str:
    """Parse a date string to ISO format (YYYY-MM-DD) or empty string.

    Handles: DD/MM/YYYY, DD/MM/YYYY HH:MM:SS, YYYY-MM-DD, YYYYMMDD.
    Returns empty string when all format attempts fail (prevents garbage
    dates from reaching Neo4j).
    """
    value = value.strip()
    if not value:
        return ""
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d", "%Y%m%d"):
        try:
            return str(pd.to_datetime(value, format=fmt).strftime("%Y-%m-%d"))
        except ValueError:
            continue
    logger.debug("Could not parse date: %r", value)
    return ""
