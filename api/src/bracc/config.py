"""Application configuration settings.

All settings are loaded from environment variables with sensible defaults.
Use .env file for local development or set env vars in production.
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment-based configuration."""

    # Neo4j Database
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"
    neo4j_database: str = "neo4j"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"
    app_env: str = "dev"

    # Security
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    rate_limit_anon: str = "60/minute"
    rate_limit_auth: str = "300/minute"
    invite_code: str = ""
    cors_origins: str = "http://localhost:3000"
    auth_cookie_name: str = "bracc_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    trust_proxy_headers: bool = False
    share_token_ttl_hours: int = 168  # 7 days

    # Product Tier
    product_tier: str = "community"

    # Feature Flags
    patterns_enabled: bool = False
    public_mode: bool = False
    public_allow_person: bool = False
    public_allow_entity_lookup: bool = False
    public_allow_investigations: bool = False

    # Pattern Analysis Settings
    pattern_split_threshold_value: float = 80000.0
    pattern_split_min_count: int = 3
    pattern_share_threshold: float = 0.6
    pattern_srp_min_orgs: int = 5
    pattern_inexig_min_recurrence: int = 3
    pattern_max_evidence_refs: int = 50

    # Pattern hardening defaults (decision-complete contract)
    pattern_temporal_window_years: int = Field(default=4, ge=1, le=20)
    pattern_min_contract_value: float = Field(default=100000.0, ge=0)
    pattern_min_contract_count: int = Field(default=2, ge=1)
    pattern_min_debt_value: float = Field(default=50000.0, ge=0)
    pattern_same_as_min_confidence: float = Field(default=0.85, ge=0, le=1)
    pattern_pep_min_confidence: float = Field(default=0.85, ge=0, le=1)
    pattern_min_recurrence: int = Field(default=2, ge=1)
    pattern_min_discrepancy_ratio: float = Field(default=0.30, ge=0, le=1)

    # AI Intelligence Settings
    ai_provider_api_key: str = ""
    ai_provider_model: str = "gpt-4"
    ai_enabled: bool = True

    # AI Cache Settings
    ai_cache_enabled: bool = Field(
        default=True,
        description="Enable AI query result caching",
    )
    ai_cache_ttl_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Cache TTL in seconds (1 min to 24 hours)",
    )
    ai_cache_max_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum cache entries",
    )

    # Web Crawling Settings
    web_crawl_timeout: float = Field(default=30.0, ge=1.0, le=120.0)
    web_crawl_max_pages: int = Field(default=10, ge=1, le=50)

    # Firecrawl Settings
    firecrawl_api_key: str = Field(
        default="",
        description="Firecrawl API key for web crawling",
    )
    firecrawl_base_url: str = Field(
        default="https://api.firecrawl.dev/v1",
        description="Firecrawl API base URL",
    )
    firecrawl_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for Firecrawl",
    )
    firecrawl_retry_delay_base: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        description="Base delay between retries in seconds",
    )
    firecrawl_deduplication_enabled: bool = Field(
        default=True,
        description="Enable content deduplication",
    )
    firecrawl_crawl_interval_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Minimum hours between crawls for same entity",
    )

    # Journalist Tools Settings
    journalist_tools_enabled: bool = True

    # Scoring Engine Settings
    scoring_sanctions_weight: float = Field(default=0.25, ge=0, le=1)
    scoring_pep_weight: float = Field(default=0.20, ge=0, le=1)
    scoring_contract_weight: float = Field(default=0.15, ge=0, le=1)
    scoring_offshore_weight: float = Field(default=0.15, ge=0, le=1)
    scoring_pattern_weight: float = Field(default=0.15, ge=0, le=1)
    scoring_temporal_weight: float = Field(default=0.10, ge=0, le=1)

    # Risk Level Thresholds
    risk_critical_threshold: float = Field(default=80.0, ge=0, le=100)
    risk_high_threshold: float = Field(default=60.0, ge=0, le=100)
    risk_medium_threshold: float = Field(default=40.0, ge=0, le=100)
    risk_low_threshold: float = Field(default=20.0, ge=0, le=100)

    # Voice Interface Settings
    voice_enabled: bool = False
    tts_voice: str = "alloy"
    tts_max_length: int = Field(default=2000, ge=100, le=5000)
    stt_model: str = "whisper-1"
    stt_min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    voice_language_detection: bool = True

    # PDF Generation Settings
    pdf_charts_enabled: bool = Field(
        default=True,
        description="Enable charts in PDF dossiers",
    )
    pdf_max_entities_per_dossier: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Maximum entities in a single dossier",
    )

    # Alert System Settings
    alert_batch_interval_minutes: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="Alert batching interval",
    )
    alert_max_per_email_per_day: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum alerts per email per day",
    )

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
