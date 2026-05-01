# Services package
from .youtube_service import YouTubeService
from .openrouter_service import OpenRouterService
from .gemini_service import GeminiService
from .notion_service import NotionService
from .storage_service import StorageService


def create_llm_service(provider: str | None = None, model: str | None = None):
    """Create the configured LLM synthesis service."""
    from backend.config import get_settings

    settings = get_settings()
    selected_provider = (provider or settings.llm_provider).strip().lower()
    selected_model = model.strip() if model and model.strip() else None

    if selected_provider == "gemini":
        return GeminiService(model=selected_model)
    if selected_provider == "openrouter":
        return OpenRouterService(model=selected_model)

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{selected_provider}'. Use 'openrouter' or 'gemini'."
    )


__all__ = [
    "YouTubeService",
    "OpenRouterService",
    "GeminiService",
    "NotionService",
    "StorageService",
    "create_llm_service",
]
