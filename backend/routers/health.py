"""Health router — GET /health."""

from fastapi import APIRouter
from backend.settings import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    """Health check — reports active AI providers."""
    # Report the model name for whichever provider is currently configured.
    provider = settings.llm_provider.lower()
    active_model = (
        settings.gemini_model if provider == "gemini" else settings.deepseek_model
    )
    return {
        "backend": "online",
        "llm_provider": settings.llm_provider,
        "llm_model": active_model,
        "embedding_provider": settings.embedding_model,
        "vector_db": "chromadb",
        "status": "healthy",
    }
