"""
自定义异常和异常处理器
Custom Exceptions and Exception Handlers
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Any
import traceback

logger = logging.getLogger(__name__)


class FileProcessingError(Exception):
    """文件处理异常"""
    
    def __init__(self, message: str, error_code: str = "FILE_PROCESSING_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class UnsupportedFileTypeError(FileProcessingError):
    """不支持的文件类型异常"""
    
    def __init__(self, file_type: str):
        message = f"不支持的文件类型: {file_type}"
        super().__init__(message, "UNSUPPORTED_FILE_TYPE")


class FileTooLargeError(FileProcessingError):
    """文件过大异常"""
    
    def __init__(self, file_size: int, max_size: int):
        message = f"文件大小 {file_size} 字节超过限制 {max_size} 字节"
        super().__init__(message, "FILE_TOO_LARGE")


class OCRError(FileProcessingError):
    """OCR处理异常"""
    
    def __init__(self, message: str):
        super().__init__(f"OCR处理失败: {message}", "OCR_ERROR")


class ChunkingError(FileProcessingError):
    """分块处理异常"""
    
    def __init__(self, message: str):
        super().__init__(f"文本分块失败: {message}", "CHUNKING_ERROR")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP异常处理器"""
    
    logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "HTTP_ERROR"
            },
            "success": False,
            "data": None
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """请求验证异常处理器"""
    
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(f"请求验证失败: {errors}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "请求参数验证失败",
                "type": "VALIDATION_ERROR",
                "details": errors
            },
            "success": False,
            "data": None
        }
    )


async def file_processing_exception_handler(request: Request, exc: FileProcessingError) -> JSONResponse:
    """文件处理异常处理器"""
    
    logger.error(f"文件处理异常: {exc.error_code} - {exc.message}")
    
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": "FILE_PROCESSING_ERROR"
            },
            "success": False,
            "data": None
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    
    # 记录详细的错误信息
    error_traceback = traceback.format_exc()
    logger.error(f"未处理的异常: {type(exc).__name__}: {str(exc)}\n{error_traceback}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
                "type": "INTERNAL_ERROR"
            },
            "success": False,
            "data": None
        }
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """设置所有异常处理器"""
    
    # HTTP异常
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # 验证异常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # 自定义异常
    app.add_exception_handler(FileProcessingError, file_processing_exception_handler)
    app.add_exception_handler(UnsupportedFileTypeError, file_processing_exception_handler)
    app.add_exception_handler(FileTooLargeError, file_processing_exception_handler)
    app.add_exception_handler(OCRError, file_processing_exception_handler)
    app.add_exception_handler(ChunkingError, file_processing_exception_handler)
    
    # 通用异常（必须放在最后）
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("异常处理器设置完成")