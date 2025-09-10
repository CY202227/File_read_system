from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from PIL import Image
import concurrent.futures
import threading

import fitz  # PyMuPDF
from openai import OpenAI

from config.settings import settings
from app.ocr.prompts import dict_promptmode_to_prompt
from config.logging_config import get_logger
from app.utils.log_utils import log_call


logger = get_logger(__name__)


class OCRReader:
    """OCR文本识别读取器，用于从PDF和图片文件中提取文本。"""
    
    def __init__(self, ocr_mode: str = "prompt_ocr"):
        """初始化OCR读取器。
        
        Args:
            ocr_mode: OCR模式，可选值为prompts.py中定义的模式
        """
        self.ocr_mode = ocr_mode
        
        # 验证OCR配置
        if not settings.OCR_MODEL_URL:
            raise ValueError("OCR_MODEL_URL 环境变量未设置")
        if not settings.OCR_MODEL_API_KEY:
            raise ValueError("OCR_MODEL_API_KEY 环境变量未设置")
            
        logger.info("初始化OCR客户端，URL: %s", settings.OCR_MODEL_URL)
        
        try:
            self.client = OpenAI(
                base_url=settings.OCR_MODEL_URL,
                api_key=settings.OCR_MODEL_API_KEY
            )
            logger.info("OCR客户端初始化成功")
        except Exception as e:
            logger.error("OCR客户端初始化失败: %s", e)
            raise ValueError(f"OCR客户端初始化失败: {e}")
    
    @log_call
    def fitz_doc_to_image(self, doc, target_dpi=200) -> Image.Image:
        """将fitz.Document转换为PIL Image。
        
        Args:
            doc: pymudoc页面
            target_dpi: 目标DPI，默认为200
            
        Returns:
            PIL Image对象
        """
        mat = fitz.Matrix(target_dpi / 72, target_dpi / 72)
        pm = doc.get_pixmap(matrix=mat, alpha=False)
        
        # 如果图像太大，使用默认DPI
        if pm.width > 4500 or pm.height > 4500:
            logger.info("图像尺寸过大，使用默认DPI")
            mat = fitz.Matrix(72 / 72, 72 / 72)  # 使用fitz默认dpi
            pm = doc.get_pixmap(matrix=mat, alpha=False)
            
        image = Image.frombytes('RGB', (pm.width, pm.height), pm.samples)
        return image
    
    @log_call
    def load_images_from_pdf(self, pdf_file: str, dpi=200, start_page_id=0, end_page_id=None) -> List[Image.Image]:
        """从PDF文件加载图像。
        
        Args:
            pdf_file: PDF文件路径
            dpi: 目标DPI
            start_page_id: 起始页码
            end_page_id: 结束页码
            
        Returns:
            图像列表
        """
        images = []
        try:
            with fitz.open(pdf_file) as doc:
                pdf_page_num = doc.page_count
                end_page_id = (
                    end_page_id
                    if end_page_id is not None and end_page_id >= 0
                    else pdf_page_num - 1
                )
                if end_page_id > pdf_page_num - 1:
                    logger.warning("结束页码超出范围，使用最大页码: %s", pdf_page_num - 1)
                    end_page_id = pdf_page_num - 1
                    
                for index in range(0, doc.page_count):
                    if start_page_id <= index <= end_page_id:
                        page = doc[index]
                        img = self.fitz_doc_to_image(page, target_dpi=dpi)
                        images.append(img)
            logger.info("从PDF加载了%s页图像", len(images))
            return images
        except Exception as e:
            logger.error("加载PDF图像失败: %s", e)
            raise
    
    @log_call
    def process_image_with_ocr(self, image: Image.Image, task_id: str = None) -> str:
        """使用OCR处理图像并返回文本内容。
        
        Args:
            image: PIL Image对象
            task_id: 任务ID，用于创建子目录
            
        Returns:
            OCR识别的文本
        """
        # 准备静态文件目录保存图像
        static_dir = Path(settings.STATIC_DIR) / "ocr_temp"
        
        # 如果有任务ID，创建子目录
        if task_id:
            task_dir = static_dir / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            save_dir = task_dir
        else:
            save_dir = static_dir
            save_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一文件名
        import uuid
        image_filename = f"ocr_image_{uuid.uuid4().hex}.png"
        image_path = save_dir / image_filename
        
        # 保存图像
        image.save(image_path)
        logger.info("图片已保存到: %s", image_path)
        
        try:
            logger.info("开始OCR处理，模式: %s", self.ocr_mode)
            # 构建OCR请求，使用完整的静态文件URL
            base_url = f"{settings.FULL_URL}"
            
            # 构建图片URL路径
            if task_id:
                image_url = f"{base_url}/static/ocr_temp/{task_id}/{image_filename}"
            else:
                image_url = f"{base_url}/static/ocr_temp/{image_filename}"
                
            logger.info("图片URL: %s", image_url)
            
            response = self.client.chat.completions.create(
                model="ocr",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": dict_promptmode_to_prompt[self.ocr_mode]},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                            },
                        },
                    ],
                }],
            )
            
            # 提取OCR结果
            ocr_text = response.choices[0].message.content or ""
            logger.debug("OCR处理完成，获取到%s字符", len(ocr_text))
            return ocr_text
        except Exception as e:
            logger.error("OCR处理失败: %s", str(e))
            logger.error("OCR服务URL: %s", settings.OCR_MODEL_URL)
            logger.error("图片文件路径: %s", image_path)
            raise RuntimeError(f"OCR处理失败: {str(e)}")
    
    @log_call
    def read_pdf_with_ocr(self, file_path: str, dpi: int = 200, task_id: str = None) -> str:
        """使用OCR读取PDF文件内容（并发处理多页以提高性能）。

        Args:
            file_path: PDF文件路径
            dpi: 图像DPI
            task_id: 任务ID，用于组织图片文件

        Returns:
            OCR识别的文本内容
        """
        logger.info("开始OCR处理PDF: %s", file_path)
        images = self.load_images_from_pdf(file_path, dpi=dpi)

        if len(images) <= 1:
            # 单页PDF，直接同步处理
            logger.info("单页PDF，直接处理")
            page_text = self.process_image_with_ocr(images[0], task_id=task_id)
            return page_text

        # 多页PDF，使用并发处理
        logger.info("多页PDF，使用并发处理，共%s页", len(images))

        # 限制并发数量，避免过多的并发请求
        max_workers = min(len(images), 5)  # 最多5个并发请求

        texts = []
        page_numbers = list(range(len(images)))

        def process_single_page(page_idx: int) -> tuple[int, str]:
            """处理单页并返回页码和文本的元组"""
            try:
                logger.info("并发处理PDF第%s/%s页", page_idx + 1, len(images))
                page_text = self.process_image_with_ocr(images[page_idx], task_id=task_id)
                return (page_idx, page_text)
            except Exception as e:
                logger.error("第%s页OCR处理失败: %s", page_idx + 1, e)
                return (page_idx, "")

        try:
            # 使用线程池并发处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_page = {
                    executor.submit(process_single_page, page_idx): page_idx
                    for page_idx in page_numbers
                }

                # 收集结果
                page_results = []
                for future in concurrent.futures.as_completed(future_to_page):
                    try:
                        page_idx, page_text = future.result()
                        page_results.append((page_idx, page_text))
                    except Exception as e:
                        logger.error("并发任务执行失败: %s", e)

                # 按页码排序结果
                page_results.sort(key=lambda x: x[0])
                texts = [text for _, text in page_results]

        except Exception as e:
            logger.warning("并发处理失败，回退到顺序处理: %s", e)
            # 回退到顺序处理
            texts = []
            for i, image in enumerate(images):
                logger.info("顺序处理PDF第%s/%s页", i+1, len(images))
                try:
                    page_text = self.process_image_with_ocr(image, task_id=task_id)
                    texts.append(page_text)
                except Exception as page_error:
                    logger.error("第%s页OCR处理失败: %s", i+1, page_error)
                    texts.append("")

        logger.info("PDF OCR处理完成，共处理%s页", len(texts))
        return "\n\n".join(texts)
    
    @log_call
    def read_image_with_ocr(self, file_path: str, task_id: str = None) -> str:
        """使用OCR读取图像文件内容。
        
        Args:
            file_path: 图像文件路径
            task_id: 任务ID，用于组织图片文件
            
        Returns:
            OCR识别的文本内容
        """
        logger.info("开始OCR处理图像: %s", file_path)
        try:
            image = Image.open(file_path)
            return self.process_image_with_ocr(image, task_id=task_id)
        except Exception as e:
            logger.error("处理图像文件失败: %s", e)
            raise
    
    @log_call
    def image_to_base64(self, image: Image.Image) -> str:
        """将PIL Image转换为Base64编码的字符串。

        Args:
            image: PIL Image对象

        Returns:
            Base64编码的字符串
        """
        import base64
        import io

        # 将图像保存到内存缓冲区
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()

        # 转换为Base64
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/png;base64,{base64_string}"

    @staticmethod
    def get_supported_extensions() -> List[str]:
        """获取OCR支持的文件扩展名列表。
        
        Returns:
            支持的文件扩展名列表
        """
        return [f".{ext}" for ext in settings.OCR_SUPPORTED_EXTENSIONS]
    
    @log_call
    def read_file_with_ocr(self, file_path: str, task_id: Optional[str] = None) -> str:
        """根据文件类型使用OCR读取文件内容。
        
        Args:
            file_path: 文件路径
            task_id: 任务ID，用于组织图片文件
            
        Returns:
            OCR识别的文本内容
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if not path.exists() or not path.is_file():
            logger.error("文件不存在: %s", file_path)
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        # 检查文件类型
        supported_extensions = self.get_supported_extensions()
        if suffix not in supported_extensions:
            logger.error("不支持的OCR文件类型: %s", suffix)
            raise ValueError(f"不支持的OCR文件类型: {suffix}")
        
        try:
            # PDF文件
            if suffix == ".pdf":
                return self.read_pdf_with_ocr(file_path, task_id=task_id)
            
            # 图像文件
            return self.read_image_with_ocr(file_path, task_id=task_id)
        except Exception as e:
            logger.error("OCR处理失败: %s", e)
            raise