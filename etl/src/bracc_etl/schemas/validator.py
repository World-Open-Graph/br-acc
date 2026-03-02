"""Schema validation utility with configurable strictness."""

import logging
import os
from typing import Any, cast

import pandas as pd

logger = logging.getLogger(__name__)


def _get_validation_mode() -> str:
    """Get validation mode from env: 'warn' (default), 'strict', or 'off'."""
    return os.environ.get("BRACC_SCHEMA_VALIDATION", "warn").lower()


def validate_dataframe(
    df: pd.DataFrame,
    schema: Any,  # pa.DataFrameSchema
    source_name: str,
) -> pd.DataFrame:
    """Validate a DataFrame against a Pandera schema.

    Behavior controlled by BRACC_SCHEMA_VALIDATION env var:
    - 'off': skip validation entirely
    - 'warn': validate, log warnings, return original df
    - 'strict': validate, raise on failure
    """
    mode = _get_validation_mode()
    if mode == "off":
        return df

    try:
        import pandera as pa

        validated = schema.validate(df, lazy=True)
        logger.info("[%s] Schema validation passed: %d rows OK", source_name, len(df))
        return cast("pd.DataFrame", validated)
    except pa.errors.SchemaErrors as exc:
        n_failures = len(exc.failure_cases)
        logger.warning(
            "[%s] Schema validation: %d failures in %d rows",
            source_name,
            n_failures,
            len(df),
        )
        for _, row in exc.failure_cases.head(10).iterrows():
            logger.warning(
                "  %s: column=%s check=%s",
                source_name,
                row.get("column"),
                row.get("check"),
            )

        if mode == "strict":
            raise
        return df  # warn mode: return original
    except ImportError:
        logger.warning("[%s] pandera not installed, skipping validation", source_name)
        return df


def validate_dataframe_sampled(
    df: pd.DataFrame,
    schema: Any,
    source_name: str,
    sample_size: int = 10_000,
) -> pd.DataFrame:
    """Validate a random sample of a large DataFrame (e.g., CNPJ).

    For DataFrames larger than sample_size, validates only a random sample
    to keep validation fast on multi-million-row datasets. Always returns
    the full original DataFrame.
    """
    if len(df) <= sample_size:
        return validate_dataframe(df, schema, source_name)

    sample = df.sample(n=sample_size, random_state=42)
    validate_dataframe(sample, schema, f"{source_name}[sample={sample_size}]")
    return df  # Always return full df
