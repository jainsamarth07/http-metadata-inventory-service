"""
Application configuration managed via environment variables.
Uses pydantic-settings for type-safe configuration with validation.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    mongodb_url: str = "mongodb://mongodb:27017"
    mongodb_db_name: str = "metadata_inventory"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    request_timeout: int = 15

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Singleton settings instance
settings = Settings()
