from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Nuxt callback
    nuxt_callback_url: str = "http://localhost:3000"
    internal_api_key: str = "change-me-to-a-random-secret"

    # Task queue
    max_concurrent_tasks: int = 2

    # Default LLM
    default_llm_provider: str = "deepseek"
    default_llm_model: str = "deepseek-chat"

    # LLM provider API keys
    deepseek_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    doubao_api_key: Optional[str] = None
    minimax_api_key: Optional[str] = None
    zhipu_api_key: Optional[str] = None
    kimi_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    model_config = {
        "env_file": "engine/.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
