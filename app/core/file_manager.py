from typing import Optional, Union, List, Dict, Any
from pathlib import Path
from app.parsers.converters.file_convert import FileConverter
from config.settings import settings
from markitdown import MarkItDown
import pandas as pd
from app.parsers.file_read.plain_text_read import read_text as read_plain_text
from app.parsers.file_read.markdown_read import MarkdownRead
from app.parsers.file_read.excel_read import ExcelRead
from app.parsers.file_read.ocr_read import OCRReader
from app.utils.log_utils import log_call
from config.logging_config import get_logger



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
        self.ocr_reader = None  # 延迟初始化OCR读取器

    @log_call
    def convert_if_needed(self) -> str:
        ext = self.input_format
        if ext == "ofd":
            return self.converter.run_convert("ofd", "pdf")
        if ext == "wps":
            return self.converter.run_convert("wps", "pdf")
        if ext == "doc":
            return self.converter.run_convert("doc", "docx")
        if ext == "xls":
            return self.converter.run_convert("xls", "xlsx")
        if ext == "ppt":
            return self.converter.run_convert("ppt", "pptx")
        if ext in settings.MEDIA_EXTENSIONS:
            return self.converter.run_convert("audio_file", "text")
        # 其他类型不需要预转换
        return self.file_path

    @log_call
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

    @log_call
    def read_text(self, *, target_format: str = "plain_text", table_precision: Optional[int] = None,
                enable_ocr: bool = True, ocr_mode: str = "prompt_ocr", task_id: Optional[str] = None) -> Union[str, pd.DataFrame, List[Dict[str, Any]]]:
        """根据目标输出格式分派到对应 reader 并返回纯文本。
        
        Args:
            target_format: 目标格式，如markdown、plain_text、dataframe等
            table_precision: 表格精度
            enable_ocr: 是否启用OCR，默认为True
            ocr_mode: OCR模式，默认为prompt_ocr
            task_id: 任务ID
            
        Returns:
            根据目标格式返回不同类型的结果
        """
        if table_precision is not None:
            try:
                pd.set_option('display.float_format', None)
                pd.set_option("display.precision", int(table_precision))
            except Exception:
                pass
                
        p = Path(self.file_path)
        suffix = p.suffix.lower()
        
        # 检查是否需要OCR处理
        is_ocr_candidate = suffix.lstrip(".") in settings.OCR_SUPPORTED_EXTENSIONS
        logger = get_logger(__name__)
        
        # PDF文件必须使用OCR处理
        is_pdf = suffix.lower() == ".pdf"
        
        if (enable_ocr and is_ocr_candidate) or is_pdf:
            logger.info("开始OCR处理文件: %s, 文件类型: %s", self.file_path, suffix)
            # 延迟初始化OCR读取器
            try:
                if self.ocr_reader is None:
                    logger.info("初始化OCR读取器, 模式: %s", ocr_mode)
                    self.ocr_reader = OCRReader(ocr_mode=ocr_mode)
                
                # 使用OCR处理文件
                logger.info("调用OCR处理文件: %s", self.file_path)
                ocr_text = self.ocr_reader.read_file_with_ocr(self.file_path, task_id=task_id)
                logger.info("OCR处理成功, 获取到%s字符的文本", len(ocr_text))
                
                # 将OCR结果保存为txt文件
                output_dir = Path(settings.STATIC_DIR) / "ocr_results"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / f"{p.stem}_ocr.txt"
                output_file.write_text(ocr_text, encoding="utf-8")
                logger.info("OCR结果已保存到: %s", output_file)
                
                # 如果目标格式是plain_text，直接返回OCR文本
                if target_format == "plain_text":
                    return ocr_text
                
                # 如果需要其他格式，使用保存的txt文件继续处理
                self.file_path = str(output_file)
            except Exception as e:
                # OCR失败时记录详细错误，但继续尝试常规方法
                logger.error("OCR处理失败: %s", str(e))
                logger.exception("OCR处理异常详情")
        
        # 常规处理流程
        if target_format == "markdown":
            return MarkdownRead().markdown_convert(self.file_path)
        if target_format == "plain_text":
            return read_plain_text(self.file_path, suffix)
        if target_format == "dataframe":
            return ExcelRead.dataframe_read(self.file_path)
        raise ValueError("不受支持的目标类型")
