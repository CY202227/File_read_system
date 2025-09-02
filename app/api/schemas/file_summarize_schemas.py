"""
文件总结相关的数据模型
File summarization related schemas
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class FileSummarizeRequest(BaseModel):
    """文件总结请求模型"""
    
    # 必需参数
    task_id: str = Field(..., description="任务ID，用于跟踪处理进度")
    
    # 总结相关参数
    summary_length: int = Field(
        default=500, 
        ge=100, 
        le=2000, 
        description="总结长度（字符数）"
    )
    summary_focus: List[str] = Field(
        default=["main_points", "key_findings", "recommendations"], 
        description="总结重点关注的方面"
    )
    summary_return_top_k: Optional[int] = Field(
        default=None,
        ge=1,
        description="返回前K条要点/段落"
    )


class FileSummarizeResponse(BaseModel):
    """文件总结响应模型"""
    
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="处理状态: pending/processing/completed/failed")
    progress: Optional[float] = Field(None, ge=0.0, le=100.0, description="处理进度百分比")
    
    # 处理结果
    summary: str = Field(default="", description="总结文本")
    summary_dict: Dict[str, str] = Field(default_factory=dict, description="结构化总结（按要点）")
    
    # 元数据
    processing_time: Optional[float] = Field(None, description="处理耗时（秒）")
    summary_meta: Optional[Dict[str, Any]] = Field(None, description="总结元数据")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息（如果处理失败）")
    error_details: Optional[Dict[str, Any]] = Field(None, description="详细错误信息")
