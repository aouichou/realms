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
        """Get multi-provider configuration with dynamic priorities based on mistral_enabled"""
        mistral_priority = 1 if self.mistral_enabled else 99
        qwen_priority = 2 if self.mistral_enabled else 1

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
        }


# Global settings instance
settings = Settings()
