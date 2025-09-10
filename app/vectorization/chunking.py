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
    logger.info(f"_windowed: size={size}, overlap={overlap}")
    if size <= 0:
        return [text]
    if overlap >= size:
        logger.warning(f"_windowed: overlap {overlap} >= size {size}, adjusting to {size-1}")
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


def _windowed_no_overlap(text: str, size: int) -> List[str]:
    """无重叠的窗口切分，确保chunk之间完全没有重叠"""
    if size <= 0:
        return [text]
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + size)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = end  # 没有overlap，直接跳到下一个位置
    return chunks


def _split_on_separators(text: str, separators: Sequence[str], keep_delimiters: bool = True) -> List[str]:
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
            if keep_delimiters:
                buffer += part
        else:
            if buffer and keep_delimiters:
                merged.append((part or "") + buffer)
                buffer = ""
            else:
                if part:
                    merged.append(part)
    if buffer and keep_delimiters:
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
                if overlap > 0:
                    chunks.extend(_windowed(candidate, size=size, overlap=overlap))
                else:
                    # 当overlap=0时，直接按size切分，不产生重叠
                    chunks.extend(_windowed_no_overlap(candidate, size=size))
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
        if overlap > 0:
            chunks.extend(_windowed(candidate, size=size, overlap=overlap))
        else:
            # 当overlap=0时，直接按size切分，不产生重叠
            chunks.extend(_windowed_no_overlap(candidate, size=size))
    return chunks


def level6_custom_delimiter_splitting(
    text: str, *, delimiter: str, config: Optional[ChunkingConfig] = None
) -> List[str]:
    """按自定义分隔符切分，完全按照delimiter边界切分，不受字数限制。

    - delimiter: 非空字符串，支持多字符。若为空则退化为整体文本。
    - 支持转义字符：\\n (换行), \\t (制表), \\r (回车)
    - 行为：完全按照delimiter进行切分，每发现一个delimiter就创建一个新的分块。
    """
    print("delimiter1: ", delimiter)
    if not delimiter:
        return [text]  # 如果没有分隔符，返回整个文本作为一个块

    # 处理转义字符
    processed_delimiter = delimiter

    if delimiter == "\\n":
        processed_delimiter = "\n"
    elif delimiter == "\\t":
        processed_delimiter = "\t"
    elif delimiter == "\\r":
        processed_delimiter = "\r"
    elif delimiter == "\\n\\n":
        processed_delimiter = "\n\n"
    else:
        # 只对包含转义字符的字符串进行unicode_escape处理
        if '\\' in delimiter:
            try:
                processed_delimiter = delimiter.encode().decode('unicode_escape')
            except Exception:
                pass  # 如果处理失败，使用原始分隔符

    # 使用split方法按delimiter切分，这样每发现一个delimiter就会创建一个新的分块
    print("delimiter: ", processed_delimiter)
    chunks = text.split(processed_delimiter)

    # 过滤掉空块，只保留非空内容
    filtered_chunks = [chunk for chunk in chunks if chunk.strip()]

    # 如果过滤后没有内容，返回原始文本
    if not filtered_chunks:
        return [text]

    return filtered_chunks

def custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
    text: str, *, delimiter: str, config: Optional[ChunkingConfig] = None
) -> List[str]:
    """按自定义分隔符切分，但保留markdown表格完整，其他文字智能合并到接近chunk_size。

    - delimiter: 非空字符串，支持多字符。若为空则退化为整体文本。
    - 支持转义字符：\\n (换行), \\t (制表), \\r (回车)
    - 行为：识别markdown表格并保持完整，其他文字按delimiter切分后智能合并，确保每块尽可能接近chunk_size。
    """
    cfg = config or ChunkingConfig()
    if not delimiter:
        return [text]  # 如果没有分隔符，返回整个文本作为一个块

    # 处理转义字符
    processed_delimiter = delimiter
    if delimiter == "\\n":
        processed_delimiter = "\n"
    elif delimiter == "\\t":
        processed_delimiter = "\t"
    elif delimiter == "\\r":
        processed_delimiter = "\r"
    elif delimiter == "\\n\\n":
        processed_delimiter = "\n\n"
    # 处理其他可能的转义序列
    else:
        processed_delimiter = delimiter.encode().decode('unicode_escape')
    
    lines = text.splitlines()
    blocks: List[Tuple[str, str]] = []
    
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        
        # 识别markdown表格：包含|的行，且下一行是分隔符行
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[i + 1]):
            buf = [line, lines[i + 1]]
            i += 2
            # 继续收集表格行，直到遇到不包含|的行或空行
            while i < n and ("|" in lines[i]) and lines[i].strip() != "":
                buf.append(lines[i])
                i += 1
            blocks.append(("table", "\n".join(buf)))
            continue
        
        # 其他内容按普通文本处理
        buf = [line]
        i += 1
        while i < n and not ("|" in lines[i] and i + 1 < n and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[i + 1])):
            buf.append(lines[i])
            i += 1
        if buf:
            blocks.append(("text", "\n".join(buf)))
    
    # 按原始顺序处理每个块，保持顺序
    chunks: List[str] = []
    current_text_chunks: List[str] = []  # 当前正在合并的文本块
    current_size = 0
    
    for block_type, content in blocks:
        if block_type == "table":
            # 如果之前有未处理的文本块，先处理它们
            if current_text_chunks:
                merged_chunks = _smart_merge_text_segments(current_text_chunks, cfg.chunk_size, cfg.chunk_overlap)
                chunks.extend(merged_chunks)
                current_text_chunks = []
                current_size = 0
            
            # 表格保持完整，不进行切分
            chunks.append(content)
        else:
            # 普通文本按delimiter切分
            if processed_delimiter in content:
                text_chunks = content.split(processed_delimiter)
                for chunk in text_chunks:
                    if chunk.strip():  # 跳过空块
                        chunk_size = len(chunk.strip())
                        
                        # 如果当前块为空，直接添加
                        if not current_text_chunks:
                            current_text_chunks.append(chunk.strip())
                            current_size = chunk_size
                            continue
                        
                        # 计算添加这个段落后的总大小（包括分隔符）
                        separator_size = 2  # "\n\n" 的长度
                        new_size = current_size + separator_size + chunk_size
                        
                        # 如果添加后仍然小于等于目标大小，或者当前块太小（小于目标大小的50%），则添加
                        if new_size <= cfg.chunk_size or current_size < cfg.chunk_size * 0.5:
                            current_text_chunks.append(chunk.strip())
                            current_size = new_size
                        else:
                            # 当前块已经足够大，保存并开始新块
                            chunks.append("\n\n".join(current_text_chunks))
                            current_text_chunks = [chunk.strip()]
                            current_size = chunk_size
            else:
                # 如果没有找到delimiter，直接添加
                if content.strip():
                    chunk_size = len(content.strip())
                    
                    if not current_text_chunks:
                        current_text_chunks.append(content.strip())
                        current_size = chunk_size
                    else:
                        separator_size = 2
                        new_size = current_size + separator_size + chunk_size
                        
                        if new_size <= cfg.chunk_size or current_size < cfg.chunk_size * 0.5:
                            current_text_chunks.append(content.strip())
                            current_size = new_size
                        else:
                            chunks.append("\n\n".join(current_text_chunks))
                            current_text_chunks = [content.strip()]
                            current_size = chunk_size
    
    # 处理最后剩余的文本块
    if current_text_chunks:
        merged_chunks = _smart_merge_text_segments(current_text_chunks, cfg.chunk_size, cfg.chunk_overlap)
        chunks.extend(merged_chunks)
    
    return chunks


def _smart_merge_text_segments(segments: List[str], target_size: int, overlap: int) -> List[str]:
    """智能合并文本段落，确保每块尽可能接近target_size。
    
    Args:
        segments: 文本段落列表
        target_size: 目标块大小
        overlap: 重叠大小（在这个实现中主要用于计算，实际合并时不使用）
    
    Returns:
        合并后的文本块列表
    """
    if not segments:
        return []
    
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_size = 0
    
    for segment in segments:
        segment_size = len(segment)
        
        # 如果当前块为空，直接添加
        if not current_chunk:
            current_chunk.append(segment)
            current_size = segment_size
            continue
        
        # 计算添加这个段落后的总大小（包括分隔符）
        separator_size = 2  # "\n\n" 的长度
        new_size = current_size + separator_size + segment_size
        
        # 如果添加后仍然小于等于目标大小，或者当前块太小（小于目标大小的50%），则添加
        if new_size <= target_size or current_size < target_size * 0.5:
            current_chunk.append(segment)
            current_size = new_size
        else:
            # 当前块已经足够大，保存并开始新块
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [segment]
            current_size = segment_size
    
    # 处理最后一个块
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks

# -----------------------------
# Interfaces
# -----------------------------


@dataclass
class ChunkingConfig:
    chunk_size: int = settings.DEFAULT_CHUNK_SIZE
    chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP
    separators: Tuple[str, ...] = ("\n\n", "\n", ", ", " ")


# -----------------------------
# Level 1: Character Splitting
# -----------------------------


def level1_character_splitting(text: str, config: Optional[ChunkingConfig] = None) -> List[str]:
    cfg = config or ChunkingConfig()
    logger.info(f"level1_character_splitting: chunk_size={cfg.chunk_size}, chunk_overlap={cfg.chunk_overlap}")
    return _windowed(text, size=cfg.chunk_size, overlap=cfg.chunk_overlap)


# -------------------------------------------------------------
# Level 2: Recursive Character Text Splitting (by separators)
# -------------------------------------------------------------


def level2_recursive_character_splitting(
    text: str, config: Optional[ChunkingConfig] = None
) -> List[str]:
    cfg = config or ChunkingConfig()
    # 当overlap=0时，不保留分隔符以避免重叠
    keep_delimiters = cfg.chunk_overlap > 0
    parts = _split_on_separators(text, cfg.separators, keep_delimiters=keep_delimiters)
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
    # 当overlap=0时，不保留分隔符以避免重叠
    keep_delimiters = cfg.chunk_overlap > 0
    parts = _split_on_separators(text, separators, keep_delimiters=keep_delimiters)
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
    # 当overlap=0时，不保留分隔符以避免重叠
    keep_delimiters = cfg.chunk_overlap > 0
    for page in page_sections:
        parts = _split_on_separators(page, ("\n\n", "\n", " "), keep_delimiters=keep_delimiters)
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
    buffer_size: int = 1,
) -> List[str]:
    """
    Level 4: 语义分割
    基于embedding语义相似度进行文本分割，保持语义相关内容在同一chunk中
    
    Args:
        text: 要分割的文本
        ai_client: AI客户端用于生成embeddings
        config: 分割配置
        similarity_drop_threshold: 语义相似度阈值，低于此值将产生分割点
        buffer_size: 句子组合窗口大小，用于减少噪音
    """
    import re
    import numpy as np
    
    cfg = config or ChunkingConfig()
    client = ai_client or AIClient()

    # 步骤1: 将文本分割为句子
    # 基于句号、问号、感叹号分割，不要求后面必须有空格
    sentences = re.split(r'(?<=[；;。？！?!])', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= 1:
        return [text]

    # 步骤2: 创建句子组合窗口（减少噪音，增强语义连贯性）
    combined_sentences = []
    for i in range(len(sentences)):
        # 组合当前句子及其前后buffer_size个句子
        start_idx = max(0, i - buffer_size)
        end_idx = min(len(sentences), i + buffer_size + 1)
        combined = ''.join(sentences[start_idx:end_idx])
        combined_sentences.append({
            'original_index': i,
            'sentence': sentences[i],
            'combined': combined
        })

    # 步骤3: 为组合句子生成embeddings
    combined_texts = [item['combined'] for item in combined_sentences]
    embeddings = client.embed_texts(combined_texts)
    
    # 将embeddings添加到句子数据中
    for i, embedding in enumerate(embeddings):
        combined_sentences[i]['embedding'] = embedding

    # 步骤4: 计算相邻句子间的余弦距离，寻找语义边界
    distances = []
    for i in range(len(combined_sentences) - 1):
        current_emb = combined_sentences[i]['embedding']
        next_emb = combined_sentences[i + 1]['embedding']
        
        similarity = _cosine_similarity(current_emb, next_emb)
        distance = 1 - similarity
        distances.append(distance)
        combined_sentences[i]['distance_to_next'] = distance

    # 步骤5: 找到语义断点（距离高于阈值的位置）
    # 使用百分位数作为动态阈值，避免硬编码阈值的问题
    if distances:
        percentile_threshold = float(np.percentile(distances, 95))
        effective_threshold = max(similarity_drop_threshold, percentile_threshold)
    else:
        effective_threshold = similarity_drop_threshold
    
    # 语义边界点
    boundary_indices = [0]  # 总是从0开始
    for i, distance in enumerate(distances):
        if distance > effective_threshold:
            boundary_indices.append(i + 1)
    boundary_indices.append(len(sentences))  # 总是在最后结束

    # 步骤6: 根据语义边界合并句子成chunks
    semantic_chunks = []
    for start, end in zip(boundary_indices, boundary_indices[1:]):
        chunk_sentences = sentences[start:end]
        chunk_text = ' '.join(chunk_sentences)
        
        # 如果单个语义chunk太大，需要进一步分割但保持语义完整性
        if len(chunk_text) > cfg.chunk_size * 2:
            # 在语义chunk内部寻找次级分割点
            sub_chunks = _split_large_semantic_chunk(
                chunk_text, chunk_sentences, cfg.chunk_size, cfg.chunk_overlap
            )
            semantic_chunks.extend(sub_chunks)
        else:
            semantic_chunks.append(chunk_text)

    return [chunk for chunk in semantic_chunks if chunk.strip()]


def _split_large_semantic_chunk(
    chunk_text: str, 
    sentences: List[str], 
    target_size: int, 
    overlap: int
) -> List[str]:
    """
    对过大的语义chunk进行二级分割，尽量保持句子完整性
    """
    if len(chunk_text) <= target_size:
        return [chunk_text]
    
    sub_chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # 如果添加这个句子会超出目标大小
        if current_chunk and len(current_chunk + sentence) > target_size:
            # 保存当前chunk
            if current_chunk:
                sub_chunks.append(current_chunk)
            
            # 开始新chunk，考虑overlap
            if overlap > 0 and current_chunk:
                # 使用完整句子作为overlap，而不是截断字符
                current_chunk = sentence
            else:
                current_chunk = sentence
        else:
            # 添加句子到当前chunk
            if current_chunk:
                current_chunk += sentence
            else:
                current_chunk = sentence
    
    # 添加最后一个chunk
    if current_chunk:
        sub_chunks.append(current_chunk)
    
    return sub_chunks


# --------------------------------------------------------------
# Level 5: Agentic Splitting (LLM-guided, experimental)
# --------------------------------------------------------------


AGENT_SPLIT_SYSTEM = (
    "你是一个专业的文档切分专家，你擅长根据用户提供的文字进行分段，"
    "分段的目的是进行更好的RAG召回，你需要根据语义自定义切块"
    "并返回一个JSON数组，数组中的每个元素是一个字符串，表示一个段落。"

)


def _split_text_into_sentences(text: str) -> List[str]:
    """
    将文本按句子分割，支持中英文句号、问号、感叹号等分隔符
    """
    # 使用正则表达式分割句子，保持分隔符
    sentences = re.split(r'(?<=[。！？?!；;])', text.strip())
    # 过滤掉空句子
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


def _estimate_token_count(text: str) -> int:
    """
    估算文本的token数量（粗略估算，中文大约1个汉字=1.5个token，英文大约1个词=1.3个token）
    这里使用简单的方法：中文字符按1.5倍，英文字符按0.3倍估算
    """
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text)
    english_chars = total_chars - chinese_chars

    # 中文字符估算为1.5个token，英文字符估算为0.3个token
    estimated_tokens = chinese_chars * 1.5 + english_chars * 0.3
    return int(estimated_tokens)


def _batch_sentences_for_token_limit(sentences: List[str], max_tokens: int = 8000) -> List[List[str]]:
    """
    将句子列表按token限制分成多个批次
    留出2000个token作为prompt和系统消息的空间
    """
    batches = []
    current_batch = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = _estimate_token_count(sentence)

        # 如果添加这个句子会超过限制，开始新批次
        if current_tokens + sentence_tokens > max_tokens and current_batch:
            batches.append(current_batch)
            current_batch = [sentence]
            current_tokens = sentence_tokens
        else:
            current_batch.append(sentence)
            current_tokens += sentence_tokens

    # 添加最后一个批次
    if current_batch:
        batches.append(current_batch)

    return batches


def _merge_chunks_with_llm(client: AIClient, chunks_batch: List[str], cfg: ChunkingConfig,
                          system_prompt: str, chunking_prompt: Optional[str], llm_model: Optional[str],
                          enable_thinking: bool, temperature: float, extra_body: Optional[Dict[str, Any]]) -> List[str]:
    """
    使用LLM合并句子批次为chunks
    """
    # 将批次中的句子重新组合成文本
    batch_text = ''.join(chunks_batch)

    # 构建prompt
    user_prompt = (
        (chunking_prompt or "Split the following text into chunks respecting a target size of ")
        + f"{cfg.chunk_size} characters with an overlap of {cfg.chunk_overlap}. "
        + "Output JSON array only.\n\n"
        + batch_text
    )

    # 调用LLM
    content = client.chat_invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model_name=llm_model,
        max_tokens=10000,  # 直接写死最大token数
        enable_thinking=enable_thinking,
        temperature=temperature,
        extra_body=extra_body,
    )

    # 解析JSON结果
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if match:
        try:
            import json
            arr = json.loads(match.group(0))
            return [str(x) for x in arr if isinstance(x, (str, int, float))]
        except Exception:
            # 如果解析失败，使用递归字符分割作为fallback
            return level2_recursive_character_splitting(batch_text, cfg)
    else:
        # 如果没有找到JSON，使用递归字符分割作为fallback
        return level2_recursive_character_splitting(batch_text, cfg)


def level5_agentic_splitting(
    text: str,
    *,
    ai_client: Optional[AIClient] = None,
    config: Optional[ChunkingConfig] = None,
    system_prompt: Optional[str] = None,
    chunking_prompt: Optional[str] = None,
    llm_model: Optional[str] = None,
    enable_thinking: bool = False,
    temperature: float = 0.0,
    extra_body: Optional[Dict[str, Any]] = None,
) -> List[str]:
    cfg = config or ChunkingConfig()
    client = ai_client or AIClient()
    sys_prompt = system_prompt or AGENT_SPLIT_SYSTEM

    # 步骤1: 将文本按句子分割
    sentences = _split_text_into_sentences(text)
    if not sentences:
        return [text]

    logger.info(f"level5_agentic_splitting: 文本被分割为 {len(sentences)} 个句子")

    # 步骤2: 将句子分成多个批次，确保每批不超过8000个token（留出2000个token给prompt）
    sentence_batches = _batch_sentences_for_token_limit(sentences, max_tokens=8000)
    logger.info(f"level5_agentic_splitting: 句子被分为 {len(sentence_batches)} 个批次进行处理")

    # 步骤3: 对每个批次分别调用LLM进行处理
    all_chunks = []
    for i, batch in enumerate(sentence_batches):
        logger.info(f"level5_agentic_splitting: 处理第 {i+1}/{len(sentence_batches)} 个批次")
        batch_chunks = _merge_chunks_with_llm(
            client=client,
            chunks_batch=batch,
            cfg=cfg,
            system_prompt=sys_prompt,
            chunking_prompt=chunking_prompt or "Split the following text into chunks respecting a target size of ",
            llm_model=llm_model,
            enable_thinking=enable_thinking,
            temperature=temperature,
            extra_body=extra_body
        )
        all_chunks.extend(batch_chunks)

    logger.info(f"level5_agentic_splitting: LLM处理完成，共获得 {len(all_chunks)} 个chunks")

    # 步骤4: 如果总chunks太多，进行最终合并
    if len(all_chunks) > 100:  # 如果chunks太多，需要进一步合并
        logger.info("level5_agentic_splitting: chunks数量过多，进行最终合并")
        # 将chunks重新组合并再次分割
        combined_text = '\n\n'.join(all_chunks)
        all_chunks = level2_recursive_character_splitting(combined_text, cfg)

    # Enforce size constraints
    normalized: List[str] = []
    for c in all_chunks:
        if len(c) > cfg.chunk_size * 2:
            normalized.extend(_windowed(c, size=cfg.chunk_size, overlap=cfg.chunk_overlap))
        else:
            normalized.append(c)

    logger.info(f"level5_agentic_splitting: 处理完成，最终返回 {len(normalized)} 个chunks")
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
       "agentic_splitting","alternative_representation_chunking",
       "custom_delimiter_splitting","custom_delimiter_splitting_with_chunk_size_and_leave_table_alone"]
    - chunking_config: dict mirroring FileProcessRequest.chunking_config
    Returns: {"chunks": [...], "derivatives": [...]} (derivatives only for Bonus)
    """
    if not enable_chunking:
        return {"chunks": [text], "derivatives": []}

    logger.info(f"chunk_text: strategy={chunking_strategy_value}, chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
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
        delimiter = str(dconf.get("delimiter") or "")
        # 不要strip()，因为delimiter可能包（如"\n\n"）
        chunks = level6_custom_delimiter_splitting(text, delimiter=delimiter, config=cfg)
        return {"chunks": chunks, "derivatives": []}

    if strategy == "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone":
        dconf = cfg_dict.get("custom_delimiter_config") or {}
        delimiter = str(dconf.get("delimiter") or "")
        # 不要strip()，因为delimiter可能包（如"\n\n"）
        chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(text, delimiter=delimiter, config=cfg)
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
        buffer_sz = sconf.get("buffer_size", 1)  # 默认buffer_size=1
        chunks = level4_semantic_splitting(
            text, 
            ai_client=client, 
            config=cfg, 
            similarity_drop_threshold=similarity_drop,
            buffer_size=buffer_sz
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
    "level6_custom_delimiter_splitting",
    "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone",
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
# - 思路：先按较强分隔符（如 "\n\n"）切分，若结果仍过长，再逐级退化使用更弱分隔符（如 "\n"、", "、" "），
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
# Level 6: Custom Delimiter Splitting（自定义分隔符切分）
# - 思路：按用户提供的分隔符进行切分，每发现一个分隔符就创建一个新的分块。
# - 适用：希望按特定分隔符进行切分的场景。
# - 优点：灵活性高，可以按任意分隔符进行切分。
# - 缺点：需要用户提供分隔符，且分隔符不能为空,并且没有chunk的字数限制。
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
#   不同等级在生成候选块后都会进行最终的尺寸规整与重叠处理