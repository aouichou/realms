"""
Configuration management using Pydantic Settings
Loads environment variables and provides type-safe configuration
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    app_name: str = Field(default="mistral-realms", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(
        default="development", description="Environment (development/staging/production)"
    )
    debug: bool = Field(default=True, description="Debug mode")

    # API Server
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")

    # Mistral AI API
    mistral_api_key: str = Field(default="", description="Mistral AI API key")
    mistral_model: str = Field(default="mistral-small-latest", description="Default Mistral model")
    mistral_max_tokens: int = Field(default=2048, description="Maximum tokens per request")
    mistral_temperature: float = Field(default=0.7, description="Model temperature")

    # Alibaba Cloud Qwen API (DashScope)
    qwen_api_key: str = Field(default="", description="Alibaba DashScope API key")
    qwen_model: str = Field(
        default="qwen-max",
        description="Default Qwen model (qwen-max for best quality, qwen-turbo for speed, qwen-plus for balance)",
    )
    qwen_max_tokens: int = Field(default=2048, description="Maximum tokens per request")
    qwen_temperature: float = Field(default=0.7, description="Model temperature")

    # Groq API (Free Provider Pool)
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_model: str = Field(default="llama-3.3-70b-versatile", description="Default Groq model")

    # Cerebras API (Free Provider Pool)
    cerebras_api_key: str = Field(default="", description="Cerebras API key")
    cerebras_base_url: str = Field(
        default="https://api.cerebras.ai/v1", description="Cerebras API base URL"
    )
    cerebras_model: str = Field(default="llama-3.3-70b", description="Default Cerebras model")

    # Together.ai API (Free Provider Pool)
    together_api_key: str = Field(default="", description="Together.ai API key")
    together_base_url: str = Field(
        default="https://api.together.xyz/v1", description="Together.ai API base URL"
    )
    together_model: str = Field(
        default="meta-llama/Llama-3.3-70B-Instruct-Turbo", description="Default Together.ai model"
    )

    # Sambanova API (Free Provider Pool)
    sambanova_api_key: str = Field(default="", description="Sambanova API key")
    sambanova_base_url: str = Field(
        default="https://api.sambanova.ai/v1", description="Sambanova API base URL"
    )
    sambanova_model: str = Field(
        default="Meta-Llama-3.3-70B-Instruct", description="Default Sambanova model"
    )

    # Mistral Toggle
    mistral_enabled: bool = Field(
        default=True,
        description="Enable Mistral priority (true=demo mode priority 1, false=testing mode priority 99)",
    )

    # Rate Limiting
    rate_limit_per_second: int = Field(default=1, description="Requests per second limit")
    rate_limit_burst: int = Field(default=3, description="Burst capacity for rate limiting")
    rate_limit_per_minute: int = Field(default=120, description="Requests per minute limit")
    rate_limit_per_hour: int = Field(default=3000, description="Requests per hour limit")
    rate_limit_burst_threshold: int = Field(
        default=40, description="Burst threshold for DDoS protection"
    )
    rate_limit_block_duration: int = Field(default=180, description="Block duration in seconds")

    # Redis
    redis_host: str = Field(default="redis", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: str = Field(default="", description="Redis password")
    redis_url_env: str = Field(
        default="",
        alias="REDIS_URL",
        description="Full Redis URL (overrides host/port/db/password)",
    )

    # PII Encryption
    pii_encryption_key: str = Field(default="", description="Encryption key for PII data at rest")

    # SMTP Email
    smtp_host: str = Field(default="mail.smtp2go.com", description="SMTP server host")
    smtp_port: int = Field(default=2525, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    smtp_from_email: str = Field(
        default="noreply@realms.anguelz.tech", description="From email for outbound messages"
    )

    # Frontend URL (for password reset links)
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend base URL")

    # PostgreSQL
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="mistral_realms", description="PostgreSQL database")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")
    database_url_env: str = Field(
        default="",
        alias="DATABASE_URL",
        description="Full database URL (overrides individual PG vars)",
    )

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://frontend:3000",
        description="Comma-separated CORS origins",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # True Randomness (Random.org)
    use_true_randomness: bool = Field(
        default=True, description="Use Random.org for true atmospheric randomness in dice rolls"
    )
    random_org_url: str = Field(
        default="https://www.random.org/integers/", description="Random.org API endpoint"
    )
    random_pool_size: int = Field(
        default=200, description="Number of random integers to fetch per API call"
    )
    random_pool_min_threshold: int = Field(
        default=50, description="Minimum pool size before triggering refill"
    )
    random_pool_timeout: float = Field(default=30.0, description="API request timeout in seconds")

    # Observability
    tracing_enabled: bool = Field(default=False, description="Enable OpenTelemetry tracing")
    otlp_endpoint: str = Field(
        default="http://jaeger:4317", description="OTLP collector endpoint (gRPC for local Jaeger)"
    )
    service_name: str = Field(
        default="mistral-realms-backend", description="Service name for tracing"
    )

    # Grafana Cloud OTLP (direct push — no collector needed)
    grafana_otlp_endpoint: str = Field(
        default="",
        description="Grafana Cloud OTLP endpoint (e.g. https://otlp-gateway-prod-eu-west-2.grafana.net/otlp)",
    )
    grafana_cloud_instance_id: str = Field(
        default="", description="Grafana Cloud instance ID (numeric, used as OTLP username)"
    )
    grafana_cloud_api_key: str = Field(
        default="", description="Grafana Cloud API key with metrics/traces/logs write scopes"
    )

    @property
    def grafana_cloud_enabled(self) -> bool:
        """Check if Grafana Cloud OTLP export is configured"""
        return bool(
            self.grafana_otlp_endpoint
            and self.grafana_cloud_instance_id
            and self.grafana_cloud_api_key
        )

    # Seed Data (Cloudflare R2) — only needed for seeding from a fresh clone
    seed_data_r2_url: str = Field(default="", description="R2 S3-compatible endpoint for seed data")
    seed_data_r2_access_key: str = Field(
        default="", description="R2 access key for seed data bucket"
    )
    seed_data_r2_secret_key: str = Field(
        default="", description="R2 secret key for seed data bucket"
    )
    seed_data_r2_bucket: str = Field(
        default="realms-data", description="R2 bucket name for seed data"
    )

    # R2 Image Storage (Cloudflare R2 for generated scene images)
    r2_endpoint: str = Field(default="", description="R2 S3-compatible endpoint URL")
    r2_access_key: str = Field(default="", description="R2 access key ID")
    r2_secret_key: str = Field(default="", description="R2 secret access key")
    r2_images_bucket: str = Field(default="realms-images", description="R2 bucket for images")
    r2_images_public_url: str = Field(
        default="",
        description="Public URL prefix for R2 images (e.g. https://images.realms.example.com)",
    )

    @property
    def r2_images_enabled(self) -> bool:
        """Check if R2 image storage is configured"""
        return bool(self.r2_endpoint and self.r2_access_key and self.r2_secret_key)

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL (prefers REDIS_URL env var if set)"""
        if self.redis_url_env:
            # Strip surrounding quotes if present (common with .env files)
            return self.redis_url_env.strip('"').strip("'")
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL (prefers DATABASE_URL env var if set)"""
        if self.database_url_env:
            url = self.database_url_env.strip('"').strip("'")
            # Convert postgres:// to postgresql+asyncpg:// for SQLAlchemy
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def ai_providers_config(self) -> dict:
        """Get multi-provider configuration with dynamic priorities based on mistral_enabled"""
        mistral_priority = 1 if self.mistral_enabled else 99
        qwen_priority = 2 if self.mistral_enabled else 1
        free_pool_priority = 3 if self.mistral_enabled else 2

        return {
            "qwen": {
                "enabled": bool(self.qwen_api_key),
                "api_key": self.qwen_api_key,
                "model": self.qwen_model,
                "max_tokens": self.qwen_max_tokens,
                "temperature": self.qwen_temperature,
                "priority": qwen_priority,
            },
            "mistral": {
                "enabled": True,  # Always available
                "api_key": self.mistral_api_key,
                "model": self.mistral_model,
                "max_tokens": self.mistral_max_tokens,
                "temperature": self.mistral_temperature,
                "rate_limit": self.rate_limit_per_second,
                "priority": mistral_priority,  # 1 for demo, 99 for testing (emergency fallback)
            },
            "groq": {
                "enabled": bool(self.groq_api_key),
                "api_key": self.groq_api_key,
                "model": self.groq_model,
                "priority": free_pool_priority,
            },
            "cerebras": {
                "enabled": bool(self.cerebras_api_key),
                "api_key": self.cerebras_api_key,
                "model": self.cerebras_model,
                "base_url": self.cerebras_base_url,
                "priority": free_pool_priority,
            },
            "together": {
                "enabled": bool(self.together_api_key),
                "api_key": self.together_api_key,
                "model": self.together_model,
                "base_url": self.together_base_url,
                "priority": free_pool_priority,
            },
            "sambanova": {
                "enabled": bool(self.sambanova_api_key),
                "api_key": self.sambanova_api_key,
                "model": self.sambanova_model,
                "base_url": self.sambanova_base_url,
                "priority": free_pool_priority,
            },
        }


# Global settings instance
settings = Settings()
