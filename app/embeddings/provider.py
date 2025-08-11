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
        api_key = (settings.EMBEDDING_MODEL_API_KEY or "").strip()
        base_url = (settings.EMBEDDING_MODEL_URL or "").strip()
        if not api_key:
            raise ValueError("EMBEDDING_MODEL_API_KEY is required for embeddings")
        if not base_url:
            raise ValueError("EMBEDDING_MODEL_URL is required for embeddings")
        return OpenAI(api_key=api_key, base_url=base_url)  # type: ignore

    raise ValueError(f"Unsupported embedding model: {name!r}")

    