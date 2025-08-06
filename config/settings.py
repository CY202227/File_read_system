"""
应用配置文件
Application Settings Configuration
"""

import os
from typing import List
from pydantic import BaseSettings


class Settings(BaseSettings):
    """应用设置类"""
    
    # 基础设置
    APP_NAME: str = "文件阅读系统"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 服务器设置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS设置
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ]
    
    # 文件处理设置
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [
        # 文档格式
        "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
        # 文本格式
        "txt", "md", "csv", "tsv", "json", "xml",
        # 图像格式 (OCR)
        "jpg", "jpeg", "png", "tiff", "bmp", "webp",
        # 代码格式
        "py", "js", "html", "css", "java", "cpp", "c", "go", "rs",
        # 音频文件
        "mp4","mp3","wav","flac"
    ]
    
    # 目录设置
    UPLOAD_DIR: str = "uploads"
    TEMP_DIR: str = "temp"
    STATIC_DIR: str = "static"
    
    # 向量化设置
    DEFAULT_CHUNK_SIZE: int = 1000  # tokens
    DEFAULT_CHUNK_OVERLAP: int = 200  # tokens
    MAX_CHUNK_SIZE: int = 4000  # tokens
    
    # 任务队列设置
    REDIS_URL: str = "redis://localhost:6379/0"
    TASK_TIMEOUT: int = 300  # 5分钟
    

    # 日志设置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 创建全局设置实例
settings = Settings()