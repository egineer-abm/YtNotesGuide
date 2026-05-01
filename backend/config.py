"""
Configuration management using pydantic-settings.
Loads environment variables from .env file.
"""

from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )
    
    # Required API Keys
    openrouter_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("openrouter_api_key", "OPENROUTER_API_KEY")
    )
    notion_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("notion_api_key", "notion_api", "notion_token")
    )
    gemini_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("gemini_api_key", "GEMINI_API_KEY", "GOOGLE_API_KEY")
    )
    
    # Optional Notion Database ID (can be created at runtime)
    notion_database_id: Optional[str] = None
    
    # Server Settings - Render uses $PORT environment variable
    backend_host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("backend_host", "BACKEND_HOST")
    )
    backend_port: int = Field(
        default=7860,
        validation_alias=AliasChoices("backend_port", "BACKEND_PORT", "PORT")
    )
    streamlit_port: int = Field(
        default=8501,
        validation_alias=AliasChoices("streamlit_port", "STREAMLIT_PORT")
    )
    
    # LLM Settings
    llm_provider: str = Field(
        default="openrouter",
        validation_alias=AliasChoices("llm_provider", "LLM_PROVIDER")
    )
    response_max_tokens: int = Field(
        default=4096,
        validation_alias=AliasChoices("response_max_tokens", "RESPONSE_MAX_TOKENS")
    )

    # OpenRouter LLM Settings
    openrouter_model: str = Field(
        default="openrouter/free",
        validation_alias=AliasChoices("openrouter_model", "OPENROUTER_MODEL")
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("openrouter_base_url", "OPENROUTER_BASE_URL")
    )
    openrouter_site_url: str = Field(
        default="http://localhost",
        validation_alias=AliasChoices("openrouter_site_url", "OPENROUTER_SITE_URL")
    )
    openrouter_app_name: str = Field(
        default="YouTube-to-Notion Guide Generator",
        validation_alias=AliasChoices("openrouter_app_name", "OPENROUTER_APP_NAME")
    )

    # Gemini LLM Settings
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("gemini_model", "GEMINI_MODEL")
    )
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        validation_alias=AliasChoices("gemini_base_url", "GEMINI_BASE_URL")
    )

    max_tokens_per_chunk: int = Field(
        default=30000,
        validation_alias=AliasChoices("max_tokens_per_chunk", "MAX_TOKENS_PER_CHUNK")
    )
    request_timeout: int = Field(
        default=60,
        validation_alias=AliasChoices("request_timeout", "REQUEST_TIMEOUT")
    )
    
    # Processing Settings
    max_concurrent_videos: int = Field(
        default=3,
        validation_alias=AliasChoices("max_concurrent_videos", "MAX_CONCURRENT_VIDEOS")
    )
    max_videos_per_channel: int = Field(
        default=5,
        validation_alias=AliasChoices("max_videos_per_channel", "MAX_VIDEOS_PER_CHANNEL")
    )
    
    # Transcript Settings
    transcript_languages: str = Field(
        default="en,en-US,en-GB",
        validation_alias=AliasChoices("transcript_languages", "TRANSCRIPT_LANGUAGES")
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("log_level", "LOG_LEVEL")
    )
    
    @property
    def transcript_language_list(self) -> list[str]:
        """Parse transcript languages into a list."""
        return [lang.strip() for lang in self.transcript_languages.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
