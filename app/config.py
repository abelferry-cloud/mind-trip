from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import os

class Settings(BaseSettings):
    # LLM - DeepSeek (主要模型)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 传统 OpenAI（兼容性备用）
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    claude_api_key: str = ""

    # 数据库
    database_url: str = "data/memory.db"

    # 应用配置
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # 模型链：逗号分隔，使用第一个可用的模型
    model_chain: str = "openai,claude,local"
    primary_model: str = "openai"

    # 超时设置
    tool_timeout: int = 10
    agent_timeout: int = 30
    request_timeout: int = 90
    llm_retry_interval: int = 2

    @property
    def model_chain_list(self) -> List[str]:
        return [m.strip() for m in self.model_chain.split(",")]

    # Memory
    memory_dir: str = "app/workspace/memory"
    memory_file: str = "app/workspace/MEMORY.md"

    # Ollama (for embedding)
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "qwen3-embedding:0.6b"

    # RAG settings
    rag_top_k: int = 5
    rag_bm25_k1: float = 1.5
    rag_bm25_b: float = 0.75
    rag_rrf_k: int = 60
    rag_temporal_decay_days: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()

load_settings = get_settings