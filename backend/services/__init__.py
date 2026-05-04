# Services package

_SERVICE_IMPORTS = {
    "YouTubeService": ("backend.services.youtube_service", "YouTubeService"),
    "OpenRouterService": ("backend.services.openrouter_service", "OpenRouterService"),
    "GeminiService": ("backend.services.gemini_service", "GeminiService"),
    "NotionService": ("backend.services.notion_service", "NotionService"),
    "StorageService": ("backend.services.storage_service", "StorageService"),
}


def __getattr__(name: str):
    """Import services lazily so optional YouTube dependencies do not affect unrelated endpoints."""
    if name not in _SERVICE_IMPORTS:
        raise AttributeError(f"module 'backend.services' has no attribute {name!r}")

    from importlib import import_module

    module_name, attribute_name = _SERVICE_IMPORTS[name]
    service = getattr(import_module(module_name), attribute_name)
    globals()[name] = service
    return service


def create_llm_service(provider: str | None = None, model: str | None = None):
    """Create the configured LLM synthesis service."""
    from backend.config import get_settings

    settings = get_settings()
    selected_provider = (provider or settings.llm_provider).strip().lower()
    selected_model = model.strip() if model and model.strip() else None

    if selected_provider == "gemini":
        from backend.services.gemini_service import GeminiService

        return GeminiService(model=selected_model)
    if selected_provider == "openrouter":
        from backend.services.openrouter_service import OpenRouterService

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
