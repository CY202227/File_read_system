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


# MCP 测试相关的 fixtures
@pytest.fixture
async def mcp_server():
    """创建内存中的 MCP 服务器实例"""
    from app.api.mcp_routers.file_read_mcp_server import mcp
    return mcp


@pytest.fixture
async def mcp_client(mcp_server):
    """创建 MCP 客户端，连接到内存中的服务器"""
    from fastmcp import Client
    client = Client(mcp_server)
    async with client:
        yield client


@pytest.fixture
def sample_test_content():
    """提供测试用的示例文本内容"""
    return """这是一个测试文档。

第一部分：文档介绍
本文档用于测试文件处理系统的各种功能。

第二部分：功能说明
系统支持多种文件格式的处理，包括文本、图片、PDF等。

第三部分：测试内容
这里包含了一些测试用的段落和句子，用于验证系统的处理能力。

第四部分：总结
通过这些测试，可以确保系统的稳定性和可靠性。
"""


@pytest.fixture
def sample_long_content():
    """提供较长的测试文本内容，用于切片和总结测试"""
    return """人工智能技术的发展正在改变我们的生活方式。

第一章：AI技术概述

人工智能（Artificial Intelligence）是指让计算机模拟人类智能的技术。
它包括机器学习、深度学习、自然语言处理、计算机视觉等多个分支。

机器学习是AI的核心技术之一，通过算法让计算机从数据中学习规律。
深度学习则是机器学习的一个重要分支，使用神经网络模拟人脑工作方式。

第二章：应用领域

AI技术已经在医疗、金融、教育、交通等多个领域得到广泛应用。

在医疗领域，AI可以帮助医生诊断疾病，提高诊断准确率。
在金融领域，AI可以用于风险评估和投资决策。
在教育领域，AI可以提供个性化学习方案。
在交通领域，AI可以实现自动驾驶和智能交通管理。

第三章：挑战与机遇

虽然AI技术发展迅速，但也面临一些挑战。
数据隐私保护、算法偏见、就业影响等问题需要重视。

同时，AI技术也带来了巨大机遇。
它可以提高生产效率，创造新的就业岗位，推动社会进步。

第四章：未来展望

未来，AI技术将继续快速发展。
随着算力的提升和算法的优化，AI将在更多领域发挥作用。
我们期待AI技术能够为人类社会带来更多福祉。
"""