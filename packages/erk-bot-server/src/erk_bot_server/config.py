"""Server configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Server configuration loaded from environment variables.

    All settings have sensible defaults for local development.
    """

    # Redis connection
    redis_url: str = "redis://localhost:6379/0"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS settings (for frontend)
    cors_origins: list[str] = ["http://localhost:5173"]  # Vite default

    model_config = {"env_prefix": "ERK_BOT_"}
