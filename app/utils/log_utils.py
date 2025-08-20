"""
日志工具模块：提供日志装饰器和辅助函数
"""

from __future__ import annotations

import asyncio
import functools
import inspect
from typing import List, Any, Callable, TypeVar, cast

from config.logging_config import get_logger

F = TypeVar('F', bound=Callable[..., Any])


def _build_log_message(func: Callable, bound: inspect.BoundArguments) -> str:
    """构建日志消息，提取关键参数。
    
    Args:
        func: 被装饰的函数
        bound: 绑定的参数
        
    Returns:
        格式化的日志消息字符串
    """
    parts: List[str] = []
    # 可以根据需要自定义要记录的关键参数
    common_keys = ["task_id", "target_format", "purpose", "file_path"]
    
    # 添加常见参数
    for key in common_keys:
        if key in bound.arguments:
            val = bound.arguments.get(key)
            try:
                parts.append(f"{key}={val}")
            except Exception:
                parts.append(f"{key}=?")
    
    # 如果没有匹配到常见参数，尝试添加第一个参数（通常是关键参数）
    if not parts and bound.arguments:
        try:
            first_key = next(iter(bound.arguments))
            val = bound.arguments.get(first_key)
            if first_key != 'self' and first_key != 'cls':  # 排除self和cls
                parts.append(f"{first_key}={val}")
        except Exception:
            pass
    
    return ", ".join(parts)


def log_call(func: F) -> F:
    """函数调用日志装饰器，记录函数的进入和参数信息。
    
    用法:
        @log_call
        def some_function(param1, param2):
            ...
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数
    """
    sig = inspect.signature(func)
    is_coro = asyncio.iscoroutinefunction(func)
    
    @functools.wraps(func)
    async def _async_wrapped(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger(func.__module__)
        try:
            bound = sig.bind_partial(*args, **kwargs)
        except Exception:
            bound = inspect.Signature().bind_partial()
        
        logger.info("enter %s(%s)", func.__qualname__, _build_log_message(func, bound))
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error("error in %s: %s", func.__qualname__, e)
            raise
    
    @functools.wraps(func)
    def _sync_wrapped(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger(func.__module__)
        try:
            bound = sig.bind_partial(*args, **kwargs)
        except Exception:
            bound = inspect.Signature().bind_partial()
        
        logger.info("enter %s(%s)", func.__qualname__, _build_log_message(func, bound))
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error("error in %s: %s", func.__qualname__, e)
            raise
    
    return cast(F, _async_wrapped if is_coro else _sync_wrapped)
