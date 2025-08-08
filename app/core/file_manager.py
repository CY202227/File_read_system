from typing import Optional
from pathlib import Path
from app.parsers.converters.file_convert import FileConverter
from config.settings import settings
from markitdown import MarkItDown
import pandas as pd
from app.parsers.file_read.plain_text_read import read_text as read_plain_text
from app.parsers.file_read.markdown_read import MarkdownRead


class FileManager:
    """统一的文件预转换管理器。

    - ofd -> pdf（远端服务）
    - wps -> pdf（远端服务）
    - doc -> docx（本地 libreoffice）
    其他格式：直接返回原路径
    """

    def __init__(self, file_path: str, ofd_authorization: Optional[str] = None, ofd_clientid: Optional[str] = None) -> None:
        self.file_path = file_path
        self.input_format = Path(file_path).suffix.lower().lstrip(".")
        self.ofd_authorization = ofd_authorization or ""
        self.ofd_clientid = ofd_clientid or ""
        self.converter = FileConverter(self.ofd_authorization, self.ofd_clientid, self.file_path)

    def convert_if_needed(self) -> str:
        ext = self.input_format
        if ext == "ofd":
            return self.converter.run_convert("ofd", "pdf")
        if ext == "wps":
            return self.converter.run_convert("wps", "pdf")
        if ext == "doc":
            return self.converter.run_convert("doc", "docx")
        if ext in settings.MEDIA_EXTENSIONS:
            return self.converter.run_convert("audio_file", "text")
        # 其他类型不需要预转换
        return self.file_path

    def convert_to_target(self, target_format: str, task_id: Optional[str] = None) -> str:
        """将当前文件按目标格式转换并返回输出路径。

        - 目前支持: markdown, text（使用 MarkItDown 提取文本内容生成 .md / .txt）
        - 其余格式可在 converters 下扩展并在此路由
        """
        target_format = (target_format or "").lower()
        md = MarkItDown(enable_plugins=False)

        # 输出目录：static/converted/{task_id}/
        out_dir = Path(settings.STATIC_DIR) / "converted" / (task_id or "default")
        out_dir.mkdir(parents=True, exist_ok=True)

        result = md.convert(self.file_path)
        stem = Path(self.file_path).stem
        if target_format == "markdown":
            dest = out_dir / f"{stem}.md"
            dest.write_text(result.text_content or "", encoding="utf-8")
            return str(dest)
        if target_format == "text":
            dest = out_dir / f"{stem}.txt"
            dest.write_text(result.text_content or "", encoding="utf-8")
            return str(dest)

        # 默认：不转换，返回原路径
        return self.file_path

    def read_text(self, *, target_format: str = "plain_text", table_precision: Optional[int] = None) -> str:
        """根据目标输出格式分派到对应 reader 并返回纯文本。

        - target_format == "markdown" → 走 MarkdownRead（将任意受支持文件转为 Markdown 文本）
        - target_format == "text" 或默认 → 走 plain_text_read（仅读取纯文本文件；非纯文本直接报不支持）
        - 表格精度通过 pandas 选项进行前置设置
        """
        if table_precision is not None:
            try:
                pd.set_option('display.float_format', None)
                pd.set_option("display.precision", int(table_precision))
            except Exception:
                pass
        if target_format == "markdown":
            return MarkdownRead().markdown_convert(self.file_path)
        if target_format == "plain_text":
            p = Path(self.file_path)
            suffix = p.suffix.lower()
            return read_plain_text(self.file_path, suffix)
        raise ValueError("不受支持的目标类型")
