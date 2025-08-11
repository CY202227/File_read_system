from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from config.logging_config import get_logger
from config.settings import settings
from app.embeddings.provider import get_embedding_client
from app.models.provider import get_text_model, get_default_text_model_name


logger = get_logger(__name__)


class AIClient:
    """Unified AI client for embeddings and text generation.

    This wraps existing provider shims to provide a consistent interface:
    - embed_texts: returns list of embedding vectors
    - chat: returns a single assistant message text
    - complete: returns a raw completion (fallback when chat isn't appropriate)
    """

    def __init__(
        self,
        embedding_model_name: Optional[str] = None,
        text_model_name: Optional[str] = None,
    ) -> None:
        self.embedding_model_name: str = (
            (embedding_model_name or settings.EMBEDDING_MODEL or "text-embedding-ada-002").strip()
        )

        self.text_model_name: str = (
            (text_model_name or get_default_text_model_name() or "").strip()
        )
        if not self.text_model_name:
            raise ValueError(
                "QWEN3_MODEL_NAME must be configured or provided for AIClient"
            )

        # Provider clients
        self._embedding_client = get_embedding_client(self.embedding_model_name)
        self._text_client = get_text_model(self.text_model_name)

    # -------- Embeddings --------
    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        inputs = list(texts)
        if not inputs:
            return []

        logger.debug(
            "Creating embeddings: %d inputs with model %s",
            len(inputs),
            self.embedding_model_name,
        )
        response = self._embedding_client.embeddings.create(  # type: ignore[attr-defined]
            model=self.embedding_model_name,
            input=inputs,
        )
        # OpenAI-compatible response: data: List[{embedding: List[float]}]
        return [item.embedding for item in response.data]

    # -------- Text Generation (Chat) --------
    def chat_invoke(
        self,
        messages: List[Dict[str, str]],
        model_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
        enable_thinking: bool = False,
        temperature: float = 0.2,
        extra_body: Optional[Dict] = None,
        **kwargs,
    ) -> str:
        """Non-stream chat completion.

        Params align with chat_stream for consistency:
        - messages: OpenAI-compatible message list
        - model_name: override default model
        - max_tokens, temperature: generation controls
        - enable_thinking: forwarded via extra_body.chat_template_kwargs
        - extra_body: merged into request body
        - **kwargs: forwarded as-is to client.create
        """
        model = (model_name or self.text_model_name).strip()
        logger.debug("Chat request with model %s and %d messages", model, len(messages))

        # Merge extra_body with thinking flag
        merged_extra: Dict = {"chat_template_kwargs": {"enable_thinking": enable_thinking}}
        if extra_body:
            # Shallow merge at top-level
            merged_extra.update(extra_body)
            # Merge nested chat_template_kwargs if present on both
            if "chat_template_kwargs" in extra_body and isinstance(extra_body["chat_template_kwargs"], dict):
                merged_extra["chat_template_kwargs"].update(extra_body["chat_template_kwargs"])  # type: ignore[index]

        response = self._text_client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            max_tokens=max_tokens,
            extra_body=merged_extra,
            **kwargs,
        )  # type: ignore
        choice = response.choices[0]
        return (choice.message.content or "").strip()
    
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        model_name: Optional[str] = None,
        enable_thinking: bool = False,
         **kwargs):
        model = (model_name or self.text_model_name).strip()
        response = self._text_client.chat.completions.create(
            model= model,
            messages=messages,# type: ignore
            stream=True,
            extra_body={
        "chat_template_kwargs": {"enable_thinking": enable_thinking}
    },
            **kwargs
        )# type: ignore
        return response

    # -------- Text Generation (Completion) --------
    def complete(
        self,
        prompt: str,
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """Optional non-chat completion interface if needed."""
        model = (model_name or self.text_model_name).strip()
        logger.debug("Completion request with model %s", model)
        response = self._text_client.completions.create(  # type: ignore[attr-defined]
            model=model,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        return (choice.text or "").strip()


__all__ = ["AIClient"]

