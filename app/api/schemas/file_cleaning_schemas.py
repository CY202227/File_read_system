"""
数据清洗相关的数据模型
Data cleaning related schemas for RAG
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class DataClean4RAGRequest(BaseModel):
    """RAG数据清洗请求模型"""

    # 必需参数
    task_id: str = Field(..., description="任务ID，用于跟踪处理进度")


class DataClean4RAGResponse(BaseModel):
    """RAG数据清洗响应模型"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="处理状态: pending/processing/completed/failed")

    # 核心返回内容
    directory: Optional[str] = Field(None, description="提取的目录内容")
    content: Optional[str] = Field(None, description="清洗后的正文内容")

    # 精简元数据
    metadata: Optional[dict] = Field(None, description="文档元数据")

    # 处理信息
    processing_time: Optional[float] = Field(None, description="处理耗时（秒）")
    error_message: Optional[str] = Field(None, description="错误信息")


class RAGMetadata(BaseModel):
    """RAG优化的精简元数据模型"""

    # 基本标识 (必需)
    title: str = Field(..., description="文档标题")
    source_type: str = Field(..., description="内容来源类型")
    content_type: str = Field(..., description="内容类型")

    # 搜索优化 (核心)
    keywords: List[str] = Field(..., description="关键词列表")
    main_topics: List[str] = Field(..., description="主要主题列表")
    domain: str = Field(..., description="领域分类")

    # 内容结构 (重要)
    chapter_titles: List[str] = Field(..., description="章节标题列表")
    content_length: int = Field(..., description="正文字数")
