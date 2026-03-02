from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"
    neo4j_database: str = "neo4j"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"
    app_env: str = "dev"

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
    product_tier: str = "community"
    patterns_enabled: bool = False
    public_mode: bool = False
    public_allow_person: bool = False
    public_allow_entity_lookup: bool = False
    public_allow_investigations: bool = False
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

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
