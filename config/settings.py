"""
应用配置文件
Application Settings Configuration
"""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用设置类"""
    
    # 基础设置
    APP_NAME: str = "文件阅读系统"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 服务器设置
    HOST: str = "0.0.0.0"
    PORT: int = 5015
    
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
        # 特殊文档（需预转换）
        "ofd", "wps",
        # 文本格式
        "txt", "md", "csv", "tsv", "json", "xml",
        # 图像格式 (OCR)
        "jpg", "jpeg", "png", "tiff", "bmp", "webp",
        # 代码格式
        "py", "js", "html", "css", "java", "cpp", "c", "go", "rs",
        # 音频文件
        "mp4","mp3","wav","flac"
    ]
    # OCR支持的文件格式
    OCR_SUPPORTED_EXTENSIONS: List[str] = [
        "pdf", "png", "jpg", "jpeg", "bmp", "tiff", "tif"
    ]
    MEDIA_EXTENSIONS: List[str] = [
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
    TASK_TIMEOUT: int = 300  # 5分钟
    
    # 日志设置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Qwen3 API设置
    QWEN3_API_KEY: str = os.getenv("QWEN3_API_KEY", "")
    QWEN3_MODEL_NAME: str = os.getenv("QWEN3_MODEL_NAME", "")
    QWEN3_BASE_URL: str = os.getenv("QWEN3_BASE_URL", "")
    
    # 向量模型设置
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "")
    EMBEDDING_MODEL_URL: str = os.getenv("EMBEDDING_MODEL_URL", "")
    EMBEDDING_MODEL_API_KEY: str = os.getenv("EMBEDDING_MODEL_API_KEY", "")

    # API设置
    api_key: str = os.getenv("API_KEY", "your-api-key")
    
    # OFD/WPS 远端转换服务设置
    ofd_api_url: str = os.getenv("OFD_API_URL", "")

    #OCR设置
    OCR_MODEL_URL: str = os.getenv("OCR_MODEL_URL", "")
    OCR_MODEL_API_KEY: str = os.getenv("OCR_MODEL_API_KEY", "")
    OCR_MODEL_NAME: str = os.getenv("OCR_MODEL_NAME", "")

    FULL_URL: str = os.getenv("FULL_URL", "")

    # 音频API设置
    AUDIO_API_URL: str = os.getenv("AUDIO_API_URL", "")

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略未在模型中定义的多余环境变量
    )


# 创建全局设置实例
settings = Settings()