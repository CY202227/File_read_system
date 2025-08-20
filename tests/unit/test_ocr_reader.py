"""
OCRReader 单元测试 - 基于 app/ocr/test.py 的实际代码
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from PIL import Image
import fitz
import enum
from pydantic import BaseModel, Field

from app.parsers.file_read.ocr_read import OCRReader
from config.settings import settings


class SupportedPdfParseMethod(enum.Enum):
    OCR = 'ocr'
    TXT = 'txt'


class PageInfo(BaseModel):
    """The width and height of page"""
    w: float = Field(description='the width of page')
    h: float = Field(description='the height of page')


class TestOCRReader:
    """OCRReader 测试类 - 基于原始测试文件"""
    
    @pytest.fixture
    def ocr_reader(self):
        """创建OCRReader实例"""
        return OCRReader(ocr_mode="prompt_ocr")
    
    @pytest.fixture
    def mock_image(self):
        """创建模拟图像"""
        # 创建一个简单的测试图像
        image = Image.new('RGB', (100, 100), color='white')
        return image
    
    def test_init(self, ocr_reader):
        """测试OCRReader初始化"""
        assert ocr_reader.ocr_mode == "prompt_ocr"
        assert ocr_reader.client is not None
    
    def test_get_supported_extensions(self, ocr_reader):
        """测试获取支持的扩展名"""
        extensions = ocr_reader.get_supported_extensions()
        expected_extensions = [f".{ext}" for ext in settings.OCR_SUPPORTED_EXTENSIONS]
        assert extensions == expected_extensions
    
    def test_fitz_doc_to_image(self, ocr_reader):
        """测试fitz_doc_to_image - 与原始测试一致"""
        # 创建模拟的fitz文档页面
        mock_doc = Mock()
        
        # 创建正常尺寸的pixmap
        mock_pixmap = Mock()
        mock_pixmap.width = 800
        mock_pixmap.height = 600
        mock_pixmap.samples = b'\xff\xff\xff' * (800 * 600 * 3)  # 白色图像数据
        
        mock_doc.get_pixmap.return_value = mock_pixmap
        
        with patch('fitz.Matrix') as mock_matrix:
            mock_matrix.return_value = Mock()
            
            result = ocr_reader.fitz_doc_to_image(mock_doc, target_dpi=200)
            
            assert isinstance(result, Image.Image)
            mock_doc.get_pixmap.assert_called_once()
    
    def test_fitz_doc_to_image_large_image(self, ocr_reader):
        """测试大图像的处理 - 与原始测试一致"""
        # 创建模拟的fitz文档页面
        mock_doc = Mock()
        
        # 创建大尺寸的pixmap
        mock_pixmap = Mock()
        mock_pixmap.width = 5000
        mock_pixmap.height = 5000
        mock_pixmap.samples = b'\xff\xff\xff' * (5000 * 5000 * 3)
        
        mock_doc.get_pixmap.return_value = mock_pixmap
        
        with patch('fitz.Matrix') as mock_matrix:
            mock_matrix.return_value = Mock()
            
            result = ocr_reader.fitz_doc_to_image(mock_doc, target_dpi=200)
            
            assert isinstance(result, Image.Image)
            # 应该调用两次get_pixmap（第一次大尺寸，第二次默认DPI）
            assert mock_doc.get_pixmap.call_count == 2
    
    @patch('fitz.open')
    def test_load_images_from_pdf(self, mock_fitz_open, ocr_reader):
        """测试从PDF加载图像 - 与原始测试一致"""
        # 创建模拟PDF文档
        mock_doc = Mock()
        mock_doc.page_count = 2
        
        # 创建模拟页面
        mock_page1 = Mock()
        mock_page2 = Mock()
        
        # 创建模拟pixmap
        mock_pixmap = Mock()
        mock_pixmap.width = 800
        mock_pixmap.height = 600
        mock_pixmap.samples = b'\xff\xff\xff' * (800 * 600 * 3)
        
        mock_page1.get_pixmap.return_value = mock_pixmap
        mock_page2.get_pixmap.return_value = mock_pixmap
        
        mock_doc.__getitem__.side_effect = lambda i: [mock_page1, mock_page2][i]
        mock_doc.__enter__ = Mock(return_value=mock_doc)
        mock_doc.__exit__ = Mock(return_value=None)
        
        mock_fitz_open.return_value = mock_doc
        
        with patch('fitz.Matrix') as mock_matrix:
            mock_matrix.return_value = Mock()
            
            images = ocr_reader.load_images_from_pdf("test.pdf", dpi=200)
            
            assert len(images) == 2
            assert all(isinstance(img, Image.Image) for img in images)
    
    @patch('fitz.open')
    def test_load_images_from_pdf_with_page_range(self, mock_fitz_open, ocr_reader):
        """测试从PDF加载指定页面范围的图像 - 与原始测试一致"""
        # 创建模拟PDF文档
        mock_doc = Mock()
        mock_doc.page_count = 2
        
        # 创建模拟页面
        mock_page = Mock()
        mock_pixmap = Mock()
        mock_pixmap.width = 800
        mock_pixmap.height = 600
        mock_pixmap.samples = b'\xff\xff\xff' * (800 * 600 * 3)
        mock_page.get_pixmap.return_value = mock_pixmap
        
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__enter__ = Mock(return_value=mock_doc)
        mock_doc.__exit__ = Mock(return_value=None)
        
        mock_fitz_open.return_value = mock_doc
        
        with patch('fitz.Matrix') as mock_matrix:
            mock_matrix.return_value = Mock()
            
            images = ocr_reader.load_images_from_pdf("test.pdf", dpi=200, start_page_id=0, end_page_id=0)
            
            assert len(images) == 1
    
    @patch('openai.OpenAI')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    def test_process_image_with_ocr(self, mock_unlink, mock_exists, mock_mkdir, mock_openai, ocr_reader, mock_image):
        """测试OCR图像处理 - 基于实际运行结果"""
        # 模拟OpenAI客户端
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # 基于实际运行结果设置返回内容
        mock_response.choices[0].message.content = '[{"bbox": [15, 16, 172, 436], "category": "Text", "text": "[\'违法行为\', 21],\n[\'值得注意\', 17],\n[\'未成年 人\', 14],\n[\'普法教育\', 12],\n[\'身心健康\', 10],\n[\'生成式\', 10],\n[\'联系方式\', 10],\n[\'非必要\', 10],\n[\'不法行为\', 9],\n[\'民事诉讼\', 9],\n[\'高等法院\', 9],\n[\'追溯到\', 9],\n[\'事实上\', 8],\n[\'资不抵债\', 8],\n[\'接管人\', 8],\n[\'有期徒刑\', 7],\n[\'明确规定\', 7],\n[\'连带责任\', 7],\n[\'违约责任\', 7],\n[\'索取到\', 7]"}]'
        mock_client.chat.completions.create.return_value = mock_response
        ocr_reader.client = mock_client
        
        # 模拟文件操作
        mock_exists.return_value = True
        
        result = ocr_reader.process_image_with_ocr(mock_image)
        
        # 验证返回的是实际的OCR结果
        assert "违法行为" in result
        assert "值得注意" in result
        assert "未成年 人" in result
        mock_client.chat.completions.create.assert_called_once()
        mock_unlink.assert_called_once()
    
    @patch('openai.OpenAI')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    def test_process_image_with_ocr_error(self, mock_unlink, mock_exists, mock_mkdir, mock_openai, ocr_reader, mock_image):
        """测试OCR图像处理错误情况"""
        # 模拟OpenAI客户端抛出异常
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("OCR服务错误")
        ocr_reader.client = mock_client
        
        # 模拟文件操作
        mock_exists.return_value = True
        
        with pytest.raises(Exception, match="OCR服务错误"):
            ocr_reader.process_image_with_ocr(mock_image)
        
        # 确保清理文件
        mock_unlink.assert_called_once()
    
    @patch('PIL.Image.open')
    @patch.object(OCRReader, 'process_image_with_ocr')
    def test_read_image_with_ocr(self, mock_process, mock_image_open, ocr_reader):
        """测试图像文件OCR读取"""
        mock_process.return_value = '[{"bbox": [15, 16, 172, 436], "category": "Text", "text": "测试文本"}]'
        mock_image_open.return_value = Mock()
        
        result = ocr_reader.read_image_with_ocr("test.png")
        
        assert "测试文本" in result
        mock_process.assert_called_once()
    
    @patch('PIL.Image.open')
    def test_read_image_with_ocr_file_not_found(self, mock_image_open, ocr_reader):
        """测试图像文件不存在的情况"""
        mock_image_open.side_effect = FileNotFoundError("文件不存在")
        
        with pytest.raises(FileNotFoundError):
            ocr_reader.read_image_with_ocr("nonexistent.png")
    
    @patch.object(OCRReader, 'load_images_from_pdf')
    @patch.object(OCRReader, 'process_image_with_ocr')
    def test_read_pdf_with_ocr(self, mock_process, mock_load_images, ocr_reader):
        """测试PDF文件OCR读取"""
        # 模拟加载的图像
        mock_images = [Mock(), Mock()]
        mock_load_images.return_value = mock_images
        
        # 模拟OCR处理结果 - 基于实际运行结果
        mock_process.side_effect = [
            '[{"bbox": [15, 16, 172, 436], "category": "Text", "text": "页面1文本"}]',
            '[{"bbox": [15, 16, 172, 436], "category": "Text", "text": "页面2文本"}]'
        ]
        
        result = ocr_reader.read_pdf_with_ocr("test.pdf")
        
        assert "页面1文本" in result
        assert "页面2文本" in result
        assert mock_process.call_count == 2
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch.object(OCRReader, 'read_pdf_with_ocr')
    def test_read_file_with_ocr_pdf(self, mock_read_pdf, mock_is_file, mock_exists, ocr_reader):
        """测试PDF文件OCR读取"""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_read_pdf.return_value = '[{"bbox": [15, 16, 172, 436], "category": "Text", "text": "PDF OCR文本"}]'
        
        result = ocr_reader.read_file_with_ocr("test.pdf")
        
        assert "PDF OCR文本" in result
        mock_read_pdf.assert_called_once_with("test.pdf")
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch.object(OCRReader, 'read_image_with_ocr')
    def test_read_file_with_ocr_image(self, mock_read_image, mock_is_file, mock_exists, ocr_reader):
        """测试图像文件OCR读取"""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_read_image.return_value = '[{"bbox": [15, 16, 172, 436], "category": "Text", "text": "图像OCR文本"}]'
        
        result = ocr_reader.read_file_with_ocr("test.png")
        
        assert "图像OCR文本" in result
        mock_read_image.assert_called_once_with("test.png")
    
    @patch('pathlib.Path.exists')
    def test_read_file_with_ocr_file_not_found(self, mock_exists, ocr_reader):
        """测试文件不存在的情况"""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            ocr_reader.read_file_with_ocr("nonexistent.pdf")
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    def test_read_file_with_ocr_unsupported_format(self, mock_is_file, mock_exists, ocr_reader):
        """测试不支持的文件格式"""
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        with pytest.raises(ValueError, match="不支持的OCR文件类型"):
            ocr_reader.read_file_with_ocr("test.txt")
    
    @patch('openai.OpenAI')
    def test_ocr_client_initialization(self, mock_openai_class):
        """测试OCR客户端初始化 - 基于原始测试文件"""
        # 模拟OpenAI客户端
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # 创建OCRReader实例
        ocr_reader = OCRReader(ocr_mode="prompt_layout_all_en")
        
        assert ocr_reader.ocr_mode == "prompt_layout_all_en"
        assert ocr_reader.client == mock_client
        
        # 验证OpenAI客户端初始化参数
        mock_openai_class.assert_called_once_with(
            base_url=settings.OCR_MODEL_URL,
            api_key=settings.OCR_MODEL_API_KEY
        )
    
    @patch('openai.OpenAI')
    def test_ocr_api_call_format(self, mock_openai_class, ocr_reader, mock_image):
        """测试OCR API调用格式 - 基于原始测试文件"""
        # 模拟OpenAI客户端
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '[{"bbox": [15, 16, 172, 436], "category": "Text", "text": "测试文本"}]'
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # 重新初始化OCRReader以使用模拟客户端
        ocr_reader.client = mock_client
        
        with patch('pathlib.Path.mkdir'), patch('pathlib.Path.exists', return_value=True), patch('pathlib.Path.unlink'):
            result = ocr_reader.process_image_with_ocr(mock_image)
            
            # 验证API调用格式
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            
            # 验证模型名称
            assert call_args[1]['model'] == "ocr"
            
            # 验证消息格式
            messages = call_args[1]['messages']
            assert len(messages) == 1
            assert messages[0]['role'] == "user"
            
            # 验证content格式
            content = messages[0]['content']
            assert len(content) == 2
            assert content[0]['type'] == "text"
            assert content[1]['type'] == "image_url"
            assert 'image_url' in content[1]['image_url']
