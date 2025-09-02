"""
文件切片相关的数据模型
File chunking related schemas
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.schemas.file_process_schemas import (
    ChunkingStrategy,
    ChunkingConfig
)


class FileChunkRequest(BaseModel):
    """文件切片请求模型"""
    
    # 必需参数
    task_id: str = Field(..., description="任务ID，用于跟踪处理进度")
    
    # 分块相关参数
    chunking_strategy: ChunkingStrategy = Field(
        default=ChunkingStrategy(value="auto"), 
        description="分块策略（auto 自动选择）"
    )
    chunk_size: int = Field(
        default=1000, 
        ge=100, 
        le=99999999, 
        description="分块大小（字符数）"
    )
    chunk_overlap: int = Field(
        default=200, 
        ge=0, 
        le=1000, 
        description="分块重叠大小（字符数）"
    )
    # 高级分块配置
    chunking_config: Optional[ChunkingConfig] = Field(
        default=None,
        description="分块策略的具体配置参数"
    )
    
    # 验证器
    @field_validator('chunking_strategy', mode='before')
    def coerce_value_models(cls, v):
        # 兼容纯字符串写法：自动包裹为 {"value": v}
        if isinstance(v, str):
            return {"value": v}
        return v
        
    @model_validator(mode='after')
    def validate_chunk_parameters(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("分块重叠大小不能大于或等于分块大小")
        return self


class FileChunkResponse(BaseModel):
    """文件切片响应模型"""
    
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="处理状态: pending/processing/completed/failed")
    progress: Optional[float] = Field(None, ge=0.0, le=100.0, description="处理进度百分比")
    
    # 处理结果
    chunks: Optional[List[str]] = Field(None, description="文本切片结果")
    derivatives: Optional[List[Dict[str, Any]]] = Field(None, description="衍生内容（如大纲、代码块等）")
    per_file: Optional[List[Dict[str, Any]]] = Field(None, description="每个文件的切片结果")
    
    # 元数据
    processing_time: Optional[float] = Field(None, description="处理耗时（秒）")
    chunks_meta: Optional[Dict[str, Any]] = Field(None, description="切片元数据")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息（如果处理失败）")
    error_details: Optional[Dict[str, Any]] = Field(None, description="详细错误信息")
