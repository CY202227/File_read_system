from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from config.logging_config import get_logger
from config.settings import settings
from app.ai.client import AIClient


logger = get_logger(__name__)


# -----------------------------
# Common utilities
# -----------------------------


def _windowed(text: str, size: int, overlap: int) -> List[str]:
    if size <= 0:
        return [text]
    if overlap >= size:
        overlap = max(0, size - 1)
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + size)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = end - overlap
    return chunks


def _split_on_separators(text: str, separators: Sequence[str]) -> List[str]:
    if not separators:
        return [text]
    # Build regex: split keeps delimiters to compute logical boundaries
    pattern = "|".join([re.escape(sep) for sep in separators if sep])
    if not pattern:
        return [text]
    parts = re.split(f"({pattern})", text)
    # Re-attach delimiters to preceding content
    merged: List[str] = []
    buffer = ""
    for part in parts:
        if re.fullmatch(pattern, part or ""):
            buffer += part
        else:
            if buffer:
                merged.append((part or "") + buffer)
                buffer = ""
            else:
                if part:
                    merged.append(part)
    if buffer:
        merged.append(buffer)
    return [p for p in merged if p]


def _by_max_tokens(
    texts: Sequence[str],
    *,
    size: int,
    overlap: int,
) -> List[str]:
    chunks: List[str] = []
    buf: List[str] = []
    token_count = 0
    for part in texts:
        length = len(part)
        if token_count + length > size:
            if buf:
                candidate = "".join(buf)
                chunks.extend(_windowed(candidate, size=size, overlap=overlap))
                # start new buf with overlap tail
                if overlap > 0 and chunks:
                    tail = chunks[-1][-overlap:]
                    buf = [tail]
                    token_count = len(tail)
                else:
                    buf = []
                    token_count = 0
        buf.append(part)
        token_count += length
    if buf:
        candidate = "".join(buf)
        chunks.extend(_windowed(candidate, size=size, overlap=overlap))
    return chunks


# -----------------------------
# Interfaces
# -----------------------------


@dataclass
class ChunkingConfig:
    chunk_size: int = settings.DEFAULT_CHUNK_SIZE
    chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP
    separators: Tuple[str, ...] = ("\n\n", "\n", ". ", ", ", " ")


# -----------------------------
# Level 1: Character Splitting
# -----------------------------


def level1_character_splitting(text: str, config: Optional[ChunkingConfig] = None) -> List[str]:
    cfg = config or ChunkingConfig()
    return _windowed(text, size=cfg.chunk_size, overlap=cfg.chunk_overlap)


# -------------------------------------------------------------
# Level 2: Recursive Character Text Splitting (by separators)
# -------------------------------------------------------------


def level2_recursive_character_splitting(
    text: str, config: Optional[ChunkingConfig] = None
) -> List[str]:
    cfg = config or ChunkingConfig()
    parts = _split_on_separators(text, cfg.separators)
    return _by_max_tokens(parts, size=cfg.chunk_size, overlap=cfg.chunk_overlap)


# -------------------------------------------------------------
# Level 3: Document Specific Splitting (PDF, Python, Markdown)
# -------------------------------------------------------------


def _split_python_code(text: str, cfg: ChunkingConfig) -> List[str]:
    # Prefer splitting on logical blocks: imports, class/def, docstrings, then lines
    separators: Tuple[str, ...] = (
        "\n\n",
        "\nclass ",
        "\ndef ",
        "\nif __name__ == '__main__':",
        "\n# ",
        "\n",
    )
    parts = _split_on_separators(text, separators)
    return _by_max_tokens(parts, size=cfg.chunk_size, overlap=cfg.chunk_overlap)


def _split_markdown(text: str, cfg: ChunkingConfig) -> List[str]:
    # Split by headings, then paragraphs
    heading_pattern = r"\n(?=#{1,6} )"
    sections = re.split(heading_pattern, text)
    chunks: List[str] = []
    for section in sections:
        paragraphs = re.split(r"\n\n+", section)
        parts: List[str] = []
        for para in paragraphs:
            parts.extend([para, "\n\n"])  # reintroduce boundary
        if parts and parts[-1] == "\n\n":
            parts.pop()
        chunks.extend(_by_max_tokens(parts, size=cfg.chunk_size, overlap=cfg.chunk_overlap))
    return chunks


def _split_pdf_text(text: str, cfg: ChunkingConfig) -> List[str]:
    # Assume text is already extracted via upstream converter; split by pages if markers exist
    page_sections = re.split(r"\f|\n\s*---\s*page\s*break\s*---\s*\n", text, flags=re.IGNORECASE)
    chunks: List[str] = []
    for page in page_sections:
        parts = _split_on_separators(page, ("\n\n", "\n", " "))
        chunks.extend(_by_max_tokens(parts, size=cfg.chunk_size, overlap=cfg.chunk_overlap))
    return chunks


def level3_document_specific_splitting(
    text: str,
    *,
    document_type: str,
    config: Optional[ChunkingConfig] = None,
) -> List[str]:
    cfg = config or ChunkingConfig()
    doc_type = (document_type or "").lower()
    if doc_type in {"py", "python"}:
        return _split_python_code(text, cfg)
    if doc_type in {"md", "markdown"}:
        return _split_markdown(text, cfg)
    if doc_type in {"pdf"}:
        return _split_pdf_text(text, cfg)
    # Fallback to recursive splitting
    return level2_recursive_character_splitting(text, cfg)


# ----------------------------------------------
# Level 4: Semantic Splitting (Embedding walk)
# ----------------------------------------------


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def level4_semantic_splitting(
    text: str,
    *,
    ai_client: Optional[AIClient] = None,
    config: Optional[ChunkingConfig] = None,
    similarity_drop_threshold: float = 0.25,
) -> List[str]:
    cfg = config or ChunkingConfig()
    client = ai_client or AIClient()

    # Pre-split roughly, then merge by semantic walk
    rough = level2_recursive_character_splitting(text, cfg)
    # Further subdivide overly long items
    normalized: List[str] = []
    for r in rough:
        if len(r) > cfg.chunk_size * 2:
            normalized.extend(_windowed(r, size=cfg.chunk_size, overlap=cfg.chunk_overlap))
        else:
            normalized.append(r)

    if not normalized:
        return []

    embeddings = client.embed_texts(normalized)
    boundaries: List[int] = [0]
    for i in range(1, len(normalized)):
        prev_vec = embeddings[i - 1]
        cur_vec = embeddings[i]
        sim = _cosine_similarity(prev_vec, cur_vec)
        if sim < similarity_drop_threshold:
            boundaries.append(i)
    boundaries.append(len(normalized))

    chunks: List[str] = []
    for start, end in zip(boundaries, boundaries[1:]):
        merged = "".join(normalized[start:end])
        chunks.extend(_windowed(merged, size=cfg.chunk_size, overlap=cfg.chunk_overlap))
    return chunks


# --------------------------------------------------------------
# Level 5: Agentic Splitting (LLM-guided, experimental)
# --------------------------------------------------------------


AGENT_SPLIT_SYSTEM = (
    "You are an expert document segmenter. Split the user text into coherent, self-contained "
    "sections suitable for retrieval. Prefer topical cohesion and avoid splitting mid-sentence. "
    "Return a JSON array of strings; do not include explanations."
)


def level5_agentic_splitting(
    text: str,
    *,
    ai_client: Optional[AIClient] = None,
    config: Optional[ChunkingConfig] = None,
    system_prompt: Optional[str] = None,
    chunking_prompt: Optional[str] = None,
    llm_model: Optional[str] = None,
    max_tokens_per_chunk: Optional[int] = 2048,
    enable_thinking: bool = False,
    temperature: float = 0.0,
    extra_body: Optional[Dict[str, Any]] = None,
) -> List[str]:
    cfg = config or ChunkingConfig()
    client = ai_client or AIClient()

    # Provide context length guidance to the agent
    user_prompt = (
        (chunking_prompt or "Split the following text into chunks respecting a target size of ")
        + f"{cfg.chunk_size} characters with an overlap of {cfg.chunk_overlap}. "
        + "Output JSON array only.\n\n"
        + text
    )
    content = client.chat_invoke(
        [
            {"role": "system", "content": system_prompt or AGENT_SPLIT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        model_name=llm_model,
        max_tokens=max_tokens_per_chunk,
        enable_thinking=enable_thinking,
        temperature=temperature,
        extra_body=extra_body,
    )
    # Robust JSON extraction (very forgiving)
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if match:
        try:
            import json

            arr = json.loads(match.group(0))
            chunks = [str(x) for x in arr if isinstance(x, (str, int, float))]
        except Exception:
            chunks = level2_recursive_character_splitting(text, cfg)
    else:
        chunks = level2_recursive_character_splitting(text, cfg)

    # Enforce size constraints
    normalized: List[str] = []
    for c in chunks:
        if len(c) > cfg.chunk_size * 2:
            normalized.extend(_windowed(c, size=cfg.chunk_size, overlap=cfg.chunk_overlap))
        else:
            normalized.append(c)
    return normalized


# --------------------------------------------------------------
# High-level dispatcher mapped to API schema-style inputs
# --------------------------------------------------------------


def chunk_text(
    text: str,
    *,
    enable_chunking: bool,
    chunking_strategy_value: str,
    chunk_size: int,
    chunk_overlap: int,
    chunking_config: Optional[Dict[str, Any]] = None,
    ai_client: Optional[AIClient] = None,
) -> Dict[str, Any]:
    """Dispatch chunking by API-level parameters.

    - chunking_strategy_value: one of
      ["auto","character_splitting","recursive_character_splitting",
       "document_specific_splitting","semantic_splitting",
       "agentic_splitting","alternative_representation_chunking"]
    - chunking_config: dict mirroring FileProcessRequest.chunking_config
    Returns: {"chunks": [...], "derivatives": [...]} (derivatives only for Bonus)
    """
    if not enable_chunking:
        return {"chunks": [text], "derivatives": []}

    cfg = ChunkingConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    client = ai_client or AIClient()

    strategy = (chunking_strategy_value or "").strip() or "auto"
    cfg_dict = chunking_config or {}

    # Auto -> choose semantic by default
    if strategy == "auto":
        strategy = "semantic_splitting"

    if strategy == "character_splitting":
        chunks = level1_character_splitting(text, cfg)
        return {"chunks": chunks, "derivatives": []}

    if strategy == "recursive_character_splitting":
        rconf = (cfg_dict.get("recursive_splitting_config") or {})
        seps = rconf.get("separators")
        if isinstance(seps, list) and seps:
            cfg = ChunkingConfig(
                chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=tuple(seps)
            )
        chunks = level2_recursive_character_splitting(text, cfg)
        return {"chunks": chunks, "derivatives": []}

    if strategy == "document_specific_splitting":
        dconf = (cfg_dict.get("document_specific_config") or {})
        doc_type = (dconf.get("document_type") or "").strip() or "markdown"
        chunks = level3_document_specific_splitting(text, document_type=doc_type, config=cfg)
        return {"chunks": chunks, "derivatives": []}

    if strategy == "semantic_splitting":
        sconf = (cfg_dict.get("semantic_splitting_config") or {})
        # embedding_model override: rebuild client if needed
        emb_model = sconf.get("embedding_model")
        if emb_model:
            client = AIClient(embedding_model_name=emb_model)
        sim_th = sconf.get("similarity_threshold")
        similarity_drop = float(sim_th) if (sim_th is not None) else 0.25
        chunks = level4_semantic_splitting(
            text, ai_client=client, config=cfg, similarity_drop_threshold=similarity_drop
        )
        return {"chunks": chunks, "derivatives": []}

    if strategy == "agentic_splitting":
        aconf = (cfg_dict.get("agentic_splitting_config") or {})
        llm_model = aconf.get("llm_model")
        if llm_model:
            client = AIClient(
                embedding_model_name=client.embedding_model_name,
                text_model_name=llm_model,
            )
        chunks = level5_agentic_splitting(
            text,
            ai_client=client,
            config=cfg,
            system_prompt=None,
            chunking_prompt=aconf.get("chunking_prompt"),
            llm_model=llm_model,
            max_tokens_per_chunk=aconf.get("max_tokens_per_chunk", 2048),
            enable_thinking=bool(aconf.get("enable_thinking", False)),
            temperature=float(aconf.get("temperature", 0.0)),
            extra_body=aconf.get("extra_body"),
        )
        return {"chunks": chunks, "derivatives": []}

    if strategy == "alternative_representation_chunking":
        bconf = (cfg_dict.get("alternative_representation_config") or {})
        # base chunks using recursive splitting for reasonable defaults
        chunks = level2_recursive_character_splitting(text, cfg)
        derivatives = bonus_alternative_representation(
            text,
            include_outline=bool(bconf.get("include_outline", True)),
            include_code_blocks=bool(bconf.get("include_code_blocks", True)),
            include_tables=bool(bconf.get("include_tables", True)),
        )
        return {"chunks": chunks, "derivatives": derivatives}

    # Fallback
    chunks = level2_recursive_character_splitting(text, cfg)
    return {"chunks": chunks, "derivatives": []}


# ---------------------------------------------------------------------------------
# Bonus Level: Alternative Representation Chunking + Indexing (derivative signals)
# ---------------------------------------------------------------------------------


def bonus_alternative_representation(
    text: str,
    *,
    include_outline: bool = True,
    include_code_blocks: bool = True,
    include_tables: bool = True,
) -> List[Tuple[str, str]]:
    """Create derivative representations for indexing.

    Returns a list of tuples (repr_type, content), e.g. ("outline", "...")
    This can be stored alongside base chunks to enrich retrieval.
    """
    representations: List[Tuple[str, str]] = []

    if include_outline:
        # Simple heading-based outline for markdown-like docs
        headings = re.findall(r"^(#{1,6}\s+.*)$", text, flags=re.MULTILINE)
        if headings:
            outline = "\n".join(headings)
            representations.append(("outline", outline))

    if include_code_blocks:
        code_blocks = re.findall(r"```[\w+-]*\n[\s\S]*?```", text)
        for idx, block in enumerate(code_blocks):
            representations.append((f"code_block_{idx}", block))

    if include_tables:
        # Markdown-style tables
        tables = re.findall(r"\n\|.+\|\n\|[-:|\s]+\|[\s\S]*?(?=\n\n|\Z)", text)
        for idx, tbl in enumerate(tables):
            representations.append((f"table_{idx}", tbl))

    return representations


__all__ = [
    "ChunkingConfig",
    "level1_character_splitting",
    "level2_recursive_character_splitting",
    "level3_document_specific_splitting",
    "level4_semantic_splitting",
    "level5_agentic_splitting",
    "bonus_alternative_representation",
]

