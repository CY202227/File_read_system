"""
日志工具单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import inspect
from functools import wraps

from app.utils.log_utils import log_call, _build_log_message


class TestLogUtils:
    """日志工具测试类"""
    
    def test_build_log_message_with_common_keys(self):
        """测试构建包含常见键的日志消息"""
        # 创建模拟的函数和绑定参数
        mock_func = Mock()
        mock_func.__name__ = "test_function"
        
        mock_bound = Mock()
        mock_bound.arguments = {
            "task_id": "task_123",
            "target_format": "markdown",
            "file_path": "/path/to/file.pdf"
        }
        
        result = _build_log_message(mock_func, mock_bound)
        
        assert "task_id=task_123" in result
        assert "target_format=markdown" in result
        assert "file_path=/path/to/file.pdf" in result
    
    def test_build_log_message_without_common_keys(self):
        """测试构建不包含常见键的日志消息"""
        mock_func = Mock()
        mock_func.__name__ = "test_function"
        
        mock_bound = Mock()
        mock_bound.arguments = {
            "param1": "value1",
            "param2": "value2"
        }
        
        result = _build_log_message(mock_func, mock_bound)
        
        # 应该包含第一个参数
        assert "param1=value1" in result
    
    def test_build_log_message_empty_arguments(self):
        """测试空参数的日志消息"""
        mock_func = Mock()
        mock_func.__name__ = "test_function"
        
        mock_bound = Mock()
        mock_bound.arguments = {}
        
        result = _build_log_message(mock_func, mock_bound)
        
        assert result == ""
    
    def test_build_log_message_with_self_cls(self):
        """测试包含self/cls参数的日志消息"""
        mock_func = Mock()
        mock_func.__name__ = "test_function"
        
        mock_bound = Mock()
        mock_bound.arguments = {
            "self": Mock(),
            "cls": Mock(),
            "param1": "value1"
        }
        
        result = _build_log_message(mock_func, mock_bound)
        
        # 应该排除self和cls，包含param1
        assert "self=" not in result
        assert "cls=" not in result
        assert "param1=value1" in result
    
    def test_build_log_message_exception_handling(self):
        """测试异常处理的日志消息"""
        mock_func = Mock()
        mock_func.__name__ = "test_function"
        
        mock_bound = Mock()
        mock_bound.arguments = {
            "task_id": Mock(side_effect=Exception("转换失败"))
        }
        
        result = _build_log_message(mock_func, mock_bound)
        
        # 应该包含错误标记
        assert "task_id=?" in result
    
    @patch('app.utils.log_utils.get_logger')
    def test_log_call_sync_function(self, mock_get_logger):
        """测试同步函数的日志装饰器"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @log_call
        def test_function(param1, param2):
            return param1 + param2
        
        result = test_function("hello", "world")
        
        assert result == "helloworld"
        mock_logger.info.assert_called_once()
        
        # 验证日志消息包含函数名和参数
        log_call_args = mock_logger.info.call_args[0]
        assert "enter test_function" in log_call_args[0]
        assert "param1=hello" in log_call_args[1]
    
    @patch('app.utils.log_utils.get_logger')
    def test_log_call_async_function(self, mock_get_logger):
        """测试异步函数的日志装饰器"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @log_call
        async def async_test_function(param1, param2):
            return param1 + param2
        
        import asyncio
        result = asyncio.run(async_test_function("hello", "world"))
        
        assert result == "helloworld"
        mock_logger.info.assert_called_once()
    
    @patch('app.utils.log_utils.get_logger')
    def test_log_call_function_with_exception(self, mock_get_logger):
        """测试函数异常的日志装饰器"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @log_call
        def test_function_with_error():
            raise ValueError("测试异常")
        
        with pytest.raises(ValueError, match="测试异常"):
            test_function_with_error()
        
        # 应该记录错误日志
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0]
        assert "error in test_function_with_error" in error_call_args[0]
        assert "测试异常" in error_call_args[1]
    
    @patch('app.utils.log_utils.get_logger')
    def test_log_call_function_with_complex_parameters(self, mock_get_logger):
        """测试复杂参数的日志装饰器"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @log_call
        def test_function(task_id, target_format, custom_param=None):
            return f"{task_id}_{target_format}_{custom_param}"
        
        result = test_function(
            task_id="task_123",
            target_format="markdown",
            custom_param={"key": "value"}
        )
        
        assert result == "task_123_markdown_{'key': 'value'}"
        mock_logger.info.assert_called_once()
        
        # 验证日志消息包含关键参数
        log_call_args = mock_logger.info.call_args[0]
        assert "task_id=task_123" in log_call_args[1]
        assert "target_format=markdown" in log_call_args[1]
    
    @patch('app.utils.log_utils.get_logger')
    def test_log_call_function_with_kwargs(self, mock_get_logger):
        """测试关键字参数的日志装饰器"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @log_call
        def test_function(**kwargs):
            return kwargs
        
        result = test_function(param1="value1", param2="value2")
        
        assert result == {"param1": "value1", "param2": "value2"}
        mock_logger.info.assert_called_once()
    
    @patch('app.utils.log_utils.get_logger')
    def test_log_call_function_with_no_parameters(self, mock_get_logger):
        """测试无参数函数的日志装饰器"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @log_call
        def test_function():
            return "no_params"
        
        result = test_function()
        
        assert result == "no_params"
        mock_logger.info.assert_called_once()
        
        # 验证日志消息格式
        log_call_args = mock_logger.info.call_args[0]
        assert "enter test_function" in log_call_args[0]
        assert log_call_args[1] == ""  # 无参数时应该为空字符串
    
    @patch('app.utils.log_utils.get_logger')
    def test_log_call_preserves_function_metadata(self, mock_get_logger):
        """测试日志装饰器保留函数元数据"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @log_call
        def test_function(param1, param2):
            """测试函数文档"""
            return param1 + param2
        
        # 验证函数元数据被保留
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "测试函数文档"
        
        # 验证函数签名
        sig = inspect.signature(test_function)
        assert len(sig.parameters) == 2
        assert "param1" in sig.parameters
        assert "param2" in sig.parameters
    
    @patch('app.utils.log_utils.get_logger')
    def test_log_call_with_bound_arguments_exception(self, mock_get_logger):
        """测试绑定参数异常的日志装饰器"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @log_call
        def test_function(param1):
            return param1
        
        # 模拟绑定参数时发生异常
        with patch('inspect.Signature.bind_partial', side_effect=Exception("绑定失败")):
            result = test_function("test_value")
            
            assert result == "test_value"
            mock_logger.info.assert_called_once()
            
            # 应该使用空的绑定参数
            log_call_args = mock_logger.info.call_args[0]
            assert "enter test_function" in log_call_args[0]
            assert log_call_args[1] == ""  # 绑定失败时应该为空字符串
