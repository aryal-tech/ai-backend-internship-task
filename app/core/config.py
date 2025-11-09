from functools import lru_cache
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Embeddings
    EMBEDDING_PROVIDER: Literal["openai", "local", "fastembed"] = "fastembed"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384
    OPENAI_API_KEY: Optional[str] = None

    # LLM
    LLM_PROVIDER: Literal["ollama", "openai"] = "ollama"
    LLM_MODEL: str = "gemma:2b"
    OLLAMA_HOST: str = "http://localhost:11434"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "docs_local"

    # MySQL
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "ai_user"
    MYSQL_PASSWORD: str = "change-me-user"
    MYSQL_DATABASE: str = "ai_backend"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def mysql_async_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()