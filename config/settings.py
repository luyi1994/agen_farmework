from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    llm_model: str = "claude-sonnet-4-6"
    llm_base_url: str = ""
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # 短期记忆（Redis）
    short_term_max_turns: int = 20
    redis_url: str = "redis://localhost:6379"
    redis_ttl: int = 3600

    # 长期记忆（Elasticsearch）
    long_term_enabled: bool = True
    es_url: str = "http://localhost:9200"
    es_username: str = ""
    es_password: str = ""
    es_index: str = "agent_memory"
    es_verify_certs: bool = False
    embedding_model: str = "all-MiniLM-L6-v2"

    # 联网搜索
    search_provider: str = "duckduckgo"  # "tavily" | "duckduckgo"
    tavily_api_key: str = ""

    # API Keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
