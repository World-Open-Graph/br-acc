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
    product_tier: str = "community"
    patterns_enabled: bool = False
    public_mode: bool = False
    public_allow_person: bool = False
    public_allow_entity_lookup: bool = False
    public_allow_investigations: bool = False

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
