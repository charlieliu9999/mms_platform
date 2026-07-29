from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "medical-match-service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@127.0.0.1:15432/acrac_db"

    REDIS_URL: str = "redis://127.0.0.1:16379/1"

    MATCH_CACHE_TTL: int = 86400 * 30
    MATCH_CACHE_MIN_CONFIDENCE: float = 0.8

    # 引擎加载模式：local=从内置包加载（独立部署），shared=从acrac_backend加载（开发期）
    ENGINE_MODE: str = "shared"

    LLM_API_BASE: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

    HOST: str = "0.0.0.0"
    PORT: int = 9100

    class Config:
        env_file = ".env"
        env_prefix = "MATCH_SVC_"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
