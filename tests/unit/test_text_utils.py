"""
文本工具模块单元测试
Unit tests for text utilities
"""

import pytest
from app.utils.text_utils import detect_text_format, validate_extension


class TestTextFormatDetection:
    """文本格式检测测试"""
    
    def test_html_detection(self):
        """测试HTML格式检测"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>测试页面</title>
        </head>
        <body>
            <h1>标题</h1>
            <p>段落内容</p>
        </body>
        </html>
        """
        assert detect_text_format(html_content) == '.html'
    
    def test_html_detection_without_doctype(self):
        """测试没有DOCTYPE的HTML检测"""
        html_content = """
        <html>
        <body>
            <div>内容</div>
            <span>文本</span>
        </body>
        </html>
        """
        assert detect_text_format(html_content) == '.html'
    
    def test_markdown_detection(self):
        """测试Markdown格式检测"""
        md_content = """
        # 主标题
        
        ## 副标题
        
        这是**粗体**文本，这是*斜体*文本。
        
        - 列表项目1
        - 列表项目2
        
        [链接文本](https://example.com)
        
        ```python
        print("代码块")
        ```
        """
        assert detect_text_format(md_content) == '.md'
    
    def test_markdown_detection_minimal(self):
        """测试最小Markdown语法检测"""
        md_content = """
        # 标题
        **粗体**
        *斜体*
        """
        assert detect_text_format(md_content) == '.md'
    
    def test_plain_text_detection(self):
        """测试纯文本检测"""
        plain_text = """
        这是纯文本内容。
        没有任何特殊格式。
        只是普通的文本。
        """
        assert detect_text_format(plain_text) == '.txt'
    
    def test_empty_content(self):
        """测试空内容"""
        assert detect_text_format("") == '.txt'
        assert detect_text_format("   ") == '.txt'
    
    def test_mixed_content(self):
        """测试混合内容（应该检测为HTML）"""
        mixed_content = """
        普通文本
        <div>HTML内容</div>
        更多文本
        """
        assert detect_text_format(mixed_content) == '.html'


class TestExtensionValidation:
    """扩展名验证测试"""
    
    def test_valid_extensions(self):
        """测试有效扩展名"""
        assert validate_extension("txt") == '.txt'
        assert validate_extension(".txt") == '.txt'
        assert validate_extension("md") == '.md'
        assert validate_extension(".md") == '.md'
        assert validate_extension("html") == '.html'
        assert validate_extension(".html") == '.html'
    
    def test_empty_extension(self):
        """测试空扩展名"""
        assert validate_extension("") == '.txt'
        assert validate_extension("   ") == '.txt'
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        assert validate_extension("TXT") == '.txt'
        assert validate_extension("Md") == '.md'
        assert validate_extension("HTML") == '.html'
    
    def test_invalid_extension(self):
        """测试无效扩展名"""
        with pytest.raises(Exception):  # HTTPException
            validate_extension("invalid")
    
    def test_whitespace_handling(self):
        """测试空白字符处理"""
        assert validate_extension("  txt  ") == '.txt'
        assert validate_extension("  .md  ") == '.md'


class TestTextFormatDetectionEdgeCases:
    """文本格式检测边界情况测试"""
    
    def test_html_like_but_not_html(self):
        """测试类似HTML但不是HTML的内容"""
        content = """
        这是一个包含 < 和 > 符号的文本
        但不是真正的HTML标签
        """
        assert detect_text_format(content) == '.txt'
    
    def test_markdown_like_but_not_markdown(self):
        """测试类似Markdown但不是Markdown的内容"""
        content = """
        这是包含 # 符号的文本
        但不是Markdown标题
        """
        # 由于没有足够的Markdown语法特征，应该检测为纯文本
        assert detect_text_format(content) == '.txt'
    
    def test_markdown_with_low_score(self):
        """测试Markdown语法较少的文本"""
        content = """
        普通文本
        # 只有一个标题
        更多普通文本
        """
        # 由于Markdown语法特征不足30%，应该检测为纯文本
        assert detect_text_format(content) == '.txt'
    
    def test_html_with_script_tags(self):
        """测试包含脚本标签的HTML"""
        content = """
        <script>
        console.log("Hello World");
        </script>
        <div>内容</div>
        """
        assert detect_text_format(content) == '.html'
    
    def test_html_with_style_tags(self):
        """测试包含样式标签的HTML"""
        content = """
        <style>
        body { color: red; }
        </style>
        <p>内容</p>
        """
        assert detect_text_format(content) == '.html'
