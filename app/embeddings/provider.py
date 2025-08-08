from typing import Optional, Any

from config.settings import settings
from config.logging_config import get_logger

from openai import OpenAI 
    


logger = get_logger(__name__)


def get_embedding_client(model_name: Optional[str] = None) -> Any:
    """Return an embedding client instance based on configured model name.

    The function reads configuration from `config.settings` and returns a client
    instance. Extend this function to support more providers/models by adding
    additional condition branches.
    """
    name = (model_name or settings.EMBEDDING_MODEL or "").strip()
    logger.info("Embedding model selected: %s", name)

    if name == "text-embedding-ada-002":
        if not settings.EMBEDDING_MODEL_API_KEY or not settings.EMBEDDING_MODEL_URL:
            raise ValueError(
                "EMBEDDING_MODEL_API_KEY and EMBEDDING_MODEL_URL must be configured for OpenAI-compatible embeddings"
            )
        # Ignore typing issues due to different OpenAI client versions/stubs
        return OpenAI(api_key=settings.EMBEDDING_MODEL_API_KEY, base_url=settings.EMBEDDING_MODEL_URL)  # type: ignore

    raise ValueError(f"Unsupported embedding model: {name!r}")

    