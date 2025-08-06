"""
上传相关的数据模型
Upload related schemas
"""

from typing import Optional
from pydantic import BaseModel, Field


class FilePathRequest(BaseModel):
    """文件路径请求模型"""
    file_path: str = Field(..., description="服务器上的文件路径")


class UploadResponse(BaseModel):
    """上传响应模型"""
    task_id: str = Field(..., description="任务ID")
    file_uuid: str = Field(..., description="文件UUID")
    original_filename: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="保存后的文件路径")
    file_size: int = Field(..., description="文件大小(bytes)")
    message: str = Field(..., description="响应消息")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细错误信息")
    task_id: Optional[str] = Field(None, description="任务ID（如果已生成）") 