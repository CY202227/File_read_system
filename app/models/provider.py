from typing import Optional, Any

from config.settings import settings
from config.logging_config import get_logger

from openai import OpenAI
logger = get_logger(__name__)




def get_default_text_model_name() -> str:
    """Return default text model name from settings."""
    return (settings.QWEN3_MODEL_NAME or "").strip()


def get_text_model(model_name: Optional[str] = None) -> Any:
    """Return a text generation model client configured for Qwen3 via OpenAI-compatible API.

    Uses `settings.QWEN3_BASE_URL`, `settings.QWEN3_API_KEY`, and the provided or default
    `model_name` (from `settings.QWEN3_MODEL_NAME`).
    """
    name = (model_name or settings.QWEN3_MODEL_NAME).strip()
    if not name:
        raise ValueError("QWEN3_MODEL_NAME must be configured or provided explicitly")

    base_url = (settings.QWEN3_BASE_URL or "").strip()
    api_key = (settings.QWEN3_API_KEY or "").strip()

    if not api_key:
        raise ValueError("QWEN3_API_KEY must be configured for Qwen3 text models")
    if not base_url:
        raise ValueError("QWEN3_BASE_URL must be configured for Qwen3 text models")

    logger.info("Text model selected: %s (Qwen3 via OpenAI-compatible API)", name)

    client_kwargs = {"api_key": api_key, "base_url": base_url}
    return OpenAI(**client_kwargs)  # type: ignore