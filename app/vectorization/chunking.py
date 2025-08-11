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


def levelX_custom_delimiter_splitting(
    text: str, *, delimiter: str, config: Optional[ChunkingConfig] = None
) -> List[str]:
    """按自定义分隔符切分，再进行尺寸规整。

    - delimiter: 非空字符串，支持多字符。若为空则退化为整体文本。
    - 行为：先以 delimiter split 得到片段，再调用 _by_max_tokens 做 size/overlap 窗口规整。
    """
    cfg = config or ChunkingConfig()
    if not delimiter:
        return _windowed(text, size=cfg.chunk_size, overlap=cfg.chunk_overlap)
    parts = text.split(delimiter)
    # 重新拼接时把分隔符作为轻边界保留在段尾，便于还原
    parts_with_boundary: List[str] = []
    for idx, p in enumerate(parts):
        if idx < len(parts) - 1:
            parts_with_boundary.append(p + delimiter)
        else:
            parts_with_boundary.append(p)
    # 为保证按分隔符返回最小粒度的块，对每个逻辑段单独进行窗口规整
    chunks: List[str] = []
    for segment in parts_with_boundary:
        chunks.extend(_windowed(segment, size=cfg.chunk_size, overlap=cfg.chunk_overlap))
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


def _split_markdown(text: str, cfg: ChunkingConfig, options: Optional[Dict[str, Any]] = None) -> List[str]:
    """Markdown 感知切分：保留代码块/表格/列表/引用等结构，尽量在语义边界切分。"""
    opts = options or {}
    preserve_headers = bool(opts.get("preserve_headers", True))
    preserve_code_blocks = bool(opts.get("preserve_code_blocks", True))
    preserve_lists = bool(opts.get("preserve_lists", True))

    lines = text.splitlines()
    blocks: List[Tuple[str, str]] = []

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # Fenced code block
        m_code = re.match(r"^\s*(```|~~~)([^`]*)$", line)
        if m_code:
            fence = m_code.group(1)
            buf: List[str] = [line]
            i += 1
            while i < n and not re.match(rf"^\s*{re.escape(fence)}\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            if i < n:
                buf.append(lines[i])
                i += 1
            blocks.append(("code", "\n".join(buf)))
            continue

        # Heading
        if re.match(r"^\s{0,3}#{1,6}\s+", line):
            buf = [line]
            i += 1
            # consume immediate following empty lines
            while i < n and lines[i].strip() == "":
                buf.append(lines[i])
                i += 1
            blocks.append(("heading", "\n".join(buf)))
            continue

        # Horizontal rule as boundary
        if re.match(r"^\s{0,3}(?:-\s?){3,}$|^\s{0,3}(?:_\s?){3,}$|^\s{0,3}(?:\*\s?){3,}$", line):
            blocks.append(("hr", line))
            i += 1
            continue

        # Table: header + separator line, then rows
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[i + 1]):
            buf = [line, lines[i + 1]]
            i += 2
            while i < n and ("|" in lines[i]) and lines[i].strip() != "":
                buf.append(lines[i])
                i += 1
            blocks.append(("table", "\n".join(buf)))
            continue

        # Blockquote
        if re.match(r"^\s*>\s?", line):
            buf = [line]
            i += 1
            while i < n and re.match(r"^\s*>\s?", lines[i]):
                buf.append(lines[i])
                i += 1
            blocks.append(("blockquote", "\n".join(buf)))
            continue

        # List block (unordered/ordered, including task list), keep consecutive list items together
        if re.match(r"^\s*(?:[-+*]|\d+[.)])\s+", line):
            buf = [line]
            i += 1
            while i < n and (re.match(r"^\s*(?:[-+*]|\d+[.)])\s+", lines[i]) or lines[i].startswith("    ") or lines[i].startswith("\t")):
                buf.append(lines[i])
                i += 1
            blocks.append(("list", "\n".join(buf)))
            continue

        # Blank line
        if line.strip() == "":
            blocks.append(("blank", line))
            i += 1
            continue

        # Paragraph (default)
        buf = [line]
        i += 1
        while i < n and lines[i].strip() != "" and not re.match(r"^\s{0,3}#{1,6}\s+|^\s*>\s?|^\s*(?:[-+*]|\d+[.)])\s+|^\s*(```|~~~)", lines[i]) and not (
            "|" in lines[i] and i + 1 < n and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[i + 1])
        ):
            buf.append(lines[i])
            i += 1
        blocks.append(("para", "\n".join(buf)))

    # Group by headings if required
    sections: List[str] = []
    if preserve_headers:
        current: List[str] = []
        for typ, content in blocks:
            if typ == "heading":
                if current:
                    sections.append("\n\n".join(current).strip())
                    current = []
                current.append(content)
            else:
                # Optionally skip code/list preservation decisions
                if typ == "code" and preserve_code_blocks:
                    current.append(content)
                elif typ == "list" and preserve_lists:
                    current.append(content)
                else:
                    current.append(content)
        if current:
            sections.append("\n\n".join(current).strip())
    else:
        # No heading grouping: each block is a part
        sections = [c for _, c in blocks if c.strip()]

    chunks: List[str] = []
    for section in [s for s in sections if s.strip()]:
        parts = [section]
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
    doc_options: Optional[Dict[str, Any]] = None,
) -> List[str]:
    cfg = config or ChunkingConfig()
    doc_type = (document_type or "").lower()
    if doc_type in {"py", "python"}:
        return _split_python_code(text, cfg)
    if doc_type in {"md", "markdown"}:
        return _split_markdown(text, cfg, options=doc_options)
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
    "你是一个专业的文档切分专家，你擅长根据用户提供的文字进行分段，"
    "分段的目的是进行更好的RAG召回，你需要根据语义自定义切块"
    "并返回一个JSON数组，数组中的每个元素是一个字符串，表示一个段落。"

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

    if strategy == "custom_delimiter_splitting":
        dconf = cfg_dict.get("custom_delimiter_config") or {}
        delimiter = str(dconf.get("delimiter") or "").strip()
        chunks = levelX_custom_delimiter_splitting(text, delimiter=delimiter, config=cfg)
        return {"chunks": chunks, "derivatives": []}

    if strategy == "document_specific_splitting":
        dconf = (cfg_dict.get("document_specific_config") or {})
        doc_type = (dconf.get("document_type") or "").strip() or "markdown"
        chunks = level3_document_specific_splitting(
            text,
            document_type=doc_type,
            config=cfg,
            doc_options={
                "preserve_headers": bool(dconf.get("preserve_headers", True)),
                "preserve_code_blocks": bool(dconf.get("preserve_code_blocks", True)),
                "preserve_lists": bool(dconf.get("preserve_lists", True)),
            },
        )
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
    "levelX_custom_delimiter_splitting",
    "bonus_alternative_representation",
]


# --------------------------------------------------------------
# 分块方法等级说明（中文）
# --------------------------------------------------------------
#
# Level 1: Character Splitting（字符级固定窗口切分）
# - 思路：按固定长度 size 对文本做滑窗切分，临近块之间保留 overlap 的字符重叠。
# - 适用：极简、对结构与语义不敏感的场景；作为其它方法不足时的兜底。
# - 优点：实现/成本最低，速度快；缺点：可能破坏语义边界、句子/段落被硬切。
#
# Level 2: Recursive Character Text Splitting（按分隔符递归退化切分）
# - 思路：先按较强分隔符（如 "\n\n"）切分，若结果仍过长，再逐级退化使用更弱分隔符（如 "\n"、". "、", "、" "），
#         同时在内部实现中保留分隔符以利于边界重建，最终再按 size/overlap 调整。
# - 适用：大多数通用文本（文章、网页纯文本等）。
# - 优点：尽量在自然边界处切分；缺点：对特定文档语法（代码/Markdown/PDF）识别有限。
#
# Level 3: Document Specific Splitting（文档特定规则）
# - 思路：针对不同文档类型使用定制化规则：
#   * Python：按 import、class/def、注释块及行级别做层次化切分。
#   * Markdown：按标题（#..######）与段落切分，尽量保留结构。
#   * PDF 文本：按分页标记与空行/空格分隔进行切分。
# - 适用：已知文档类型，且希望保留该类型的结构信息。
# - 优点：结构感更强、语义边界更自然；缺点：需维护多种类型规则。
#
# Level 4: Semantic Splitting（语义切分，基于嵌入）
# - 思路：先用 Level 2 得到粗分段，并对过长段进行二次窗口化归一化；
#         然后对相邻段计算嵌入向量余弦相似度，当相似度显著下降（低于 similarity_drop_threshold）时作为切分边界；
#         最后再按 size/overlap 做尺寸规整。
# - 适用：希望块内语义尽量一致、块间语义自然转折的检索/问答场景。
# - 优点：对主题变化敏感、块质量较高；缺点：依赖嵌入模型与调用成本。
#
# Level 5: Agentic Splitting（代理引导切分，LLM 驱动，实验性）
# - 思路：向 LLM 发送“请输出 JSON 数组”的强约束提示，让模型基于语义与长度约束主动规划切分，
#         解析失败时回退到 Level 2；产出的块再进行尺寸规整。
# - 适用：对切分质量要求更高、可接受 LLM 成本的场景；或文本体裁差异较大、规则难以穷尽时。
# - 优点：可结合任务上下文做更智能的切分决策；缺点：成本高、需要稳健的 JSON 解析与回退策略。
#
# Bonus: Alternative Representation Chunking（替代表示/索引衍生物）
# - 思路：在基础分块之外，额外抽取“可用于索引或 UI 呈现”的衍生表示，如：
#         大纲（标题集合）、代码块列表、Markdown 表格列表等。
# - 适用：检索增强、快速预览、结构化浏览等需求。
# - 说明：返回值为 (repr_type, content) 列表，可与基础 chunks 一同存储，用于下游检索与展示。
#
# 备注：
# - 调度函数 chunk_text 会将 "auto" 策略映射为 "semantic_splitting"，以取得更均衡的默认效果。
# - ChunkingConfig 中的 chunk_size 与 chunk_overlap 是所有等级的统一尺寸约束；
#   不同等级在生成候选块后都会进行最终的尺寸规整与重叠处理。
