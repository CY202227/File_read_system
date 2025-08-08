"""
上传相关的数据模型
Upload related schemas
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class FilePathRequest(BaseModel):
    """文件路径请求模型"""
    file_paths: List[str] = Field(..., description="文件路径列表（支持单个或多个文件）")
    task_id: Optional[str] = Field(None, description="可选的任务ID，如果不提供将自动生成")


class FileUploadInfo(BaseModel):
    """文件上传信息"""
    file_uuid: str = Field(..., description="文件UUID")
    original_filename: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="保存后的文件路径")
    file_size: int = Field(..., description="文件大小(bytes)")
    status: str = Field(..., description="上传状态: success/error")
    error_message: Optional[str] = Field(None, description="错误信息（如果上传失败）")


class UploadResponse(BaseModel):
    """文件上传响应模型（支持单个或多个文件）"""
    task_id: str = Field(..., description="任务ID")
    total_files: int = Field(..., description="总文件数")
    successful_uploads: int = Field(..., description="成功上传的文件数")
    failed_uploads: int = Field(..., description="失败的文件数")
    files: List[FileUploadInfo] = Field(..., description="文件上传详情列表")
    message: str = Field(..., description="响应消息")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细错误信息")
    task_id: Optional[str] = Field(None, description="任务ID（如果已生成）") 