"""应用配置（pydantic-settings + .env）。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置；密钥与连接串均从环境变量 / .env 读取。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 本机库
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mcp_agent_db"
    redis_url: str = "redis://localhost:6379/0"

    # 火山引擎（方舟）
    ark_api_key: str = ""
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_model: str = "doubao-seed-1-8-251228"
    embedding_model: str = "doubao-embedding-vision-251215"

    # 服务发现（本地）
    knowledge_mcp_url: str = "http://localhost:8101"
    memory_mcp_url: str = "http://localhost:8102"
    business_mcp_url: str = "http://localhost:8103"
    orchestrator_url: str = "http://localhost:8001"
    api_url: str = "http://localhost:8000"

    # 鉴权（MVP 可关；预留）
    auth_provider: str = "none"  # none | dev_header

    # 解析（MVP 仅 md/text）
    parser_enabled: str = "markdown,text"


@lru_cache
def get_settings() -> Settings:
    return Settings()
