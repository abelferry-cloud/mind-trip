from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import os

class Settings(BaseSettings):
    # LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    claude_api_key: str = ""

    # Database
    database_url: str = "data/memory.db"

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Model chain: comma-separated, first available is used
    model_chain: str = "openai,claude,local"
    primary_model: str = "openai"

    # Timeouts
    tool_timeout: int = 10
    agent_timeout: int = 30
    request_timeout: int = 90
    llm_retry_interval: int = 2

    @property
    def model_chain_list(self) -> List[str]:
        return [m.strip() for m in self.model_chain.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()

load_settings = get_settings