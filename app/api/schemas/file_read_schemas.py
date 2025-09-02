"""
文件读取相关的数据模型
File reading related schemas
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

from app.api.schemas.file_process_schemas import (
    ProcessingPurpose,
    OutputFormat,
    TablePrecision,
    OCRMode
)


class FileReadRequest(BaseModel):
    """文件读取请求模型"""
    
    # 必需参数
    task_id: str = Field(..., description="任务ID，用于跟踪处理进度")
    purpose: ProcessingPurpose = Field(..., description="读取文件的目的")
    target_format: OutputFormat = Field(..., description="目标输出格式")
    
    # OCR相关配置
    enable_ocr: bool = Field(default=True, description="是否启用OCR文本识别")
    ocr_mode: Optional[OCRMode] = Field(
        default=OCRMode(value="prompt_ocr"),
        description="OCR模式（prompt_ocr: 仅文本识别; prompt_layout_all_en: 包含布局信息)"
    )
    
    # 可选参数
    table_precision: Optional[TablePrecision] = Field(
        default=TablePrecision(value=10), 
        description="读取表格的精度"
    )
    
    # 验证器
    @field_validator('purpose', 'target_format', 'ocr_mode', mode='before')
    def coerce_value_models(cls, v):
        # 兼容纯字符串写法：自动包裹为 {"value": v}
        if isinstance(v, str):
            return {"value": v}
        return v

    @field_validator('table_precision', mode='before')
    def coerce_table_precision(cls, v):
        # 支持纯数值写法：自动包裹为 {"value": v}
        if isinstance(v, int):
            return {"value": v}
        return v


class FileReadResponse(BaseModel):
    """文件读取响应模型"""
    
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="处理状态: pending/processing/completed/failed")
    progress: Optional[float] = Field(None, ge=0.0, le=100.0, description="处理进度百分比")
    
    # 处理结果
    result_data: Optional[Dict[str, Any]] = Field(None, description="直接返回的结果数据")
    
    # 元数据
    processing_time: Optional[float] = Field(None, description="处理耗时（秒）")
    file_info: Optional[Dict[str, Any]] = Field(None, description="文件信息")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息（如果处理失败）")
    error_details: Optional[Dict[str, Any]] = Field(None, description="详细错误信息")
