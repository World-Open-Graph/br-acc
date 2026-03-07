"""Pandera schemas for Firecrawl ETL data validation.

Validates the DataFrames produced by firecrawl.py operations:
- crawled_pages: Individual crawled page records
- crawl_results: Aggregate crawl operation results
- entity_enrichment: Enriched entity data with web sources
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import DataFrame, Series

# ------------------------------------------------------------------
# Crawled Page Schema
# Individual crawled web page records
# ------------------------------------------------------------------
crawled_page_schema = pa.DataFrameSchema(
    columns={
        "url": pa.Column(
            str,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.str_length(
                    min_value=10,
                    error="URL must be at least 10 characters",
                ),
                pa.Check.str_startswith(
                    "http",
                    error="URL must start with http",
                ),
            ],
        ),
        "title": pa.Column(
            str,
            nullable=True,
            coerce=True,
            checks=[
                pa.Check.str_length(
                    max_value=500,
                    error="Title must be at most 500 characters",
                ),
            ],
        ),
        "content": pa.Column(
            str,
            nullable=True,
            coerce=True,
        ),
        "source": pa.Column(
            str,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.isin(
                    ["news", "company_registry", "social", "government", "unknown"],
                    error="Source must be a valid type",
                ),
            ],
        ),
        "published_at": pa.Column(
            str,
            nullable=True,
            coerce=True,
        ),
        "relevance_score": pa.Column(
            float,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.in_range(
                    min_value=0.0,
                    max_value=1.0,
                    error="Relevance score must be between 0 and 1",
                ),
            ],
        ),
        "crawl_timestamp": pa.Column(
            str,
            nullable=False,
            coerce=True,
        ),
        "content_hash": pa.Column(
            str,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.str_length(
                    min_value=8,
                    max_value=64,
                    error="Content hash must be 8-64 characters",
                ),
            ],
        ),
        "entity_id": pa.Column(
            str,
            nullable=False,
            coerce=True,
        ),
    },
    coerce=True,
    strict=False,  # Allow extra columns
)

# ------------------------------------------------------------------
# Crawl Result Schema
# Aggregate crawl operation results
# ------------------------------------------------------------------
crawl_result_schema = pa.DataFrameSchema(
    columns={
        "entity_id": pa.Column(
            str,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.str_length(
                    min_value=1,
                    error="Entity ID must not be empty",
                ),
            ],
        ),
        "total_pages": pa.Column(
            int,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.greater_than_or_equal_to(
                    0,
                    error="Total pages must be >= 0",
                ),
            ],
        ),
        "deduplicated_count": pa.Column(
            int,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.greater_than_or_equal_to(
                    0,
                    error="Deduplicated count must be >= 0",
                ),
            ],
        ),
        "last_crawled_at": pa.Column(
            str,
            nullable=False,
            coerce=True,
        ),
        "has_errors": pa.Column(
            bool,
            nullable=False,
            coerce=True,
        ),
    },
    coerce=True,
    strict=False,
)

# ------------------------------------------------------------------
# Entity Enrichment Schema
# Enriched entity data with web-sourced attributes
# ------------------------------------------------------------------
entity_enrichment_schema = pa.DataFrameSchema(
    columns={
        "entity_id": pa.Column(
            str,
            nullable=False,
            coerce=True,
        ),
        "entity_name": pa.Column(
            str,
            nullable=False,
            coerce=True,
        ),
        "identifier": pa.Column(
            str,
            nullable=True,
            coerce=True,
        ),
        "source_url": pa.Column(
            str,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.str_startswith(
                    "http",
                    error="Source URL must start with http",
                ),
            ],
        ),
        "source_title": pa.Column(
            str,
            nullable=True,
            coerce=True,
        ),
        "source_snippet": pa.Column(
            str,
            nullable=True,
            coerce=True,
        ),
        "relevance_score": pa.Column(
            float,
            nullable=False,
            coerce=True,
            checks=[
                pa.Check.in_range(
                    min_value=0.0,
                    max_value=1.0,
                    error="Relevance score must be between 0 and 1",
                ),
            ],
        ),
        "enriched_at": pa.Column(
            str,
            nullable=False,
            coerce=True,
        ),
    },
    coerce=True,
    strict=False,
)


# ------------------------------------------------------------------
# Schema validation functions
# ------------------------------------------------------------------

def validate_crawled_pages(df: pa.typing.DataFrame) -> pa.typing.DataFrame:
    """Validate crawled pages DataFrame against schema.

    Args:
        df: DataFrame to validate.

    Returns:
        Validated DataFrame.

    Raises:
        pa.errors.SchemaError: If validation fails.
    """
    return crawled_page_schema.validate(df, lazy=True)


def validate_crawl_results(df: pa.typing.DataFrame) -> pa.typing.DataFrame:
    """Validate crawl results DataFrame against schema.

    Args:
        df: DataFrame to validate.

    Returns:
        Validated DataFrame.

    Raises:
        pa.errors.SchemaError: If validation fails.
    """
    return crawl_result_schema.validate(df, lazy=True)


def validate_entity_enrichment(df: pa.typing.DataFrame) -> pa.typing.DataFrame:
    """Validate entity enrichment DataFrame against schema.

    Args:
        df: DataFrame to validate.

    Returns:
        Validated DataFrame.

    Raises:
        pa.errors.SchemaError: If validation fails.
    """
    return entity_enrichment_schema.validate(df, lazy=True)
