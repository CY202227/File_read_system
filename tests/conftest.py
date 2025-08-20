"""
pytest 配置文件
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 设置测试环境变量
    os.environ.setdefault("OCR_MODEL_URL", "http://test-ocr-server:8000")
    os.environ.setdefault("OCR_MODEL_API_KEY", "test-api-key")
    os.environ.setdefault("OCR_MODEL_NAME", "test-ocr-model")
    
    # 创建测试目录
    test_dirs = ["temp", "static", "static/ocr_temp", "static/uploads"]
    for dir_path in test_dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    yield
    
    # 清理测试文件（可选）
    # 这里可以添加测试后的清理逻辑


@pytest.fixture
def mock_settings():
    """模拟设置"""
    with patch('config.settings.settings') as mock_settings:
        mock_settings.OCR_MODEL_URL = "http://test-ocr-server:8000"
        mock_settings.OCR_MODEL_API_KEY = "test-api-key"
        mock_settings.OCR_MODEL_NAME = "test-ocr-model"
        mock_settings.OCR_SUPPORTED_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "bmp", "tiff", "tif"]
        mock_settings.STATIC_DIR = "static"
        mock_settings.TEMP_DIR = "temp"
        yield mock_settings


@pytest.fixture
def mock_openai_client():
    """模拟OpenAI客户端"""
    with patch('openai.OpenAI') as mock_client_class:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "测试OCR文本"
        mock_client.chat.completions.create.return_value = mock_response
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_pdf_path():
    """提供示例PDF文件路径"""
    return "tests/test_data/sample.pdf"


@pytest.fixture
def sample_image_path():
    """提供示例图像文件路径"""
    return "tests/test_data/sample.png"


@pytest.fixture
def sample_text_path():
    """提供示例文本文件路径"""
    return "tests/test_data/sample.txt"
