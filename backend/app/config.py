"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for TigerGraph Agentic Fraud Investigation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "TigerGraph Agentic Fraud Investigation"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # TigerGraph Configuration
    TIGERGRAPH_HOST: str = "http://127.0.0.1:9000"
    TIGERGRAPH_USERNAME: str = "tigergraph"
    TIGERGRAPH_PASSWORD: str = "tigergraph"
    TIGERGRAPH_GRAPH: str = "FraudInvestigation"
    TIGERGRAPH_SECRET: Optional[str] = None

    # Groq LLM Configuration
    GROQ_API_KEY: Optional[str] = None
    GROQ_PRIMARY_MODEL: str = "openai/gpt-oss-120b"
    GROQ_FAST_MODEL: str = "openai/gpt-oss-20b"

    # Gemini LLM Fallback Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_FALLBACK_MODEL: str = "gemini-2.0-flash"

    # Feature Flags
    ENABLE_LAYA: bool = False
    ENABLE_LIGHTGBM: bool = False
    ENABLE_LANGFUSE: bool = False

    # Storage Paths
    DATASET_PATH: Path = Path("./data/raw")
    PROCESSED_DATA_DIR: Path = Path("./data/processed")
    OUTPUT_PATH: Path = Path("./outputs")


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
