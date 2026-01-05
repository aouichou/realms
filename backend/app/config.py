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

    # Rate Limiting
    rate_limit_per_second: int = Field(default=1, description="Requests per second limit")
    rate_limit_burst: int = Field(default=3, description="Burst capacity for rate limiting")

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


# Global settings instance
settings = Settings()
