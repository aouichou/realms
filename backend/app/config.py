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

    # Google Gemini AI API
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_model: str = Field(
        default="gemini-3-flash-preview",
        description="Default Gemini model (gemini-3-flash-preview for better D&D reasoning)",
    )
    gemini_max_tokens: int = Field(default=2048, description="Maximum tokens per request")
    gemini_temperature: float = Field(default=0.7, description="Model temperature")
    gemini_thinking_level: str = Field(
        default="high",
        description="Thinking level for Gemini 3 models (minimal, low, medium, high) - high recommended for D&D DMing",
    )

    # OpenAI API
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-3.5-turbo",
        description="Default OpenAI model (gpt-3.5-turbo recommended for cost/performance balance)",
    )
    openai_max_tokens: int = Field(default=2048, description="Maximum tokens per request")
    openai_temperature: float = Field(default=0.7, description="Model temperature")

    # Anthropic API
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-3-haiku-20240307",
        description="Default Anthropic model (claude-3-haiku for cost efficiency)",
    )
    anthropic_max_tokens: int = Field(default=2048, description="Maximum tokens per request")
    anthropic_temperature: float = Field(default=0.7, description="Model temperature")

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

    # PostgreSQL
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="mistral_realms", description="PostgreSQL database")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")

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
        default="http://jaeger:4317", description="OTLP collector endpoint (Jaeger)"
    )
    service_name: str = Field(
        default="mistral-realms-backend", description="Service name for tracing"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL"""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def ai_providers_config(self) -> dict:
        """Get multi-provider configuration"""
        return {
            "gemini": {
                "enabled": bool(self.gemini_api_key),
                "api_key": self.gemini_api_key,
                "model": self.gemini_model,
                "max_tokens": self.gemini_max_tokens,
                "temperature": self.gemini_temperature,
                "thinking_level": self.gemini_thinking_level,
                "priority": 1,  # Primary (best free tier with thinking)
            },
            "mistral": {
                "enabled": bool(self.mistral_api_key),
                "api_key": self.mistral_api_key,
                "model": self.mistral_model,
                "max_tokens": self.mistral_max_tokens,
                "temperature": self.mistral_temperature,
                "rate_limit": self.rate_limit_per_second,
                "priority": 2,  # Fallback
            },
            "openai": {
                "enabled": bool(self.openai_api_key),
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "max_tokens": self.openai_max_tokens,
                "temperature": self.openai_temperature,
                "priority": 3,  # Secondary fallback
            },
            "anthropic": {
                "enabled": bool(self.anthropic_api_key),
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
                "max_tokens": self.anthropic_max_tokens,
                "temperature": self.anthropic_temperature,
                "priority": 4,  # Tertiary fallback
            },
        }


# Global settings instance
settings = Settings()
