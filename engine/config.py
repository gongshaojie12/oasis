from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    nuxt_callback_url: str = "http://localhost:3000"
    internal_api_key: str = "change-me-to-a-random-secret"
    max_concurrent_tasks: int = 2
    default_llm_provider: str = "deepseek"
    default_llm_model: str = "deepseek-chat"

    model_config = {"env_file": "engine/.env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
