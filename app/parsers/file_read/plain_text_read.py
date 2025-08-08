from pathlib import Path
from typing import Set


def read_text(file_path: str, suffix: str) -> str:
    """读取纯文本文件并返回其内容。

    - 仅对常见纯文本后缀（如 txt/csv/json/yaml 等）进行直接读取。
    - 非纯文本格式不做转换，直接报错为“不支持的文件类型（plain_text）”。
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    direct_text_suffixes: Set[str] = {
        ".txt",
        ".log",
        ".csv",
        ".tsv",
        ".json",
        ".ndjson",
        ".yaml",
        ".yml",
        ".ini",
        ".cfg",
        ".conf",
        ".properties",
        ".toml",
        ".sql",
        ".md",
        ".rst",
        ".py",
        ".java",
        ".js",
        ".ts",
        ".css",
        ".scss",
        ".less",
        ".env",
    }

    normalized_suffix = (suffix or path.suffix).lower()

    if normalized_suffix not in direct_text_suffixes:
        raise ValueError(f"不支持的文件类型（plain_text）：{normalized_suffix}")

    return path.read_text(encoding="utf-8", errors="ignore")


