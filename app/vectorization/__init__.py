from typing import Optional

from config.logging_config import get_logger
from app.embeddings.provider import get_embedding_client

logger = get_logger(__name__)


class EmbeddingModel:
    def __new__(cls, model_name: Optional[str] = None):
        logger.info("EmbeddingModel shim used; delegating to app.embeddings.provider.get_embedding_client")
        return get_embedding_client(model_name=model_name)


