"""
信息抽取相关的数据模型
Information extraction related schemas
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator

from app.api.schemas.file_process_schemas import (
    ProcessingPurpose,
    OutputFormat,
    LangExtractConfig,
    OCRMode
)


class FileExtractRequest(BaseModel):
    """信息抽取请求模型"""
    
    # 必需参数
    task_id: str = Field(..., description="任务ID，用于跟踪处理进度")
    
    # 抽取配置（必需）
    extract_config: LangExtractConfig = Field(
        ...,
        description="信息抽取配置（含 prompt 与 extractions）",
    )
    
    # 基础参数
    purpose: ProcessingPurpose = Field(
        default=ProcessingPurpose(value="content_reading"), 
        description="读取文件的目的"
    )
    target_format: OutputFormat = Field(
        default=OutputFormat(value="plain_text"), 
        description="目标输出格式"
    )
    
    # OCR相关配置
    enable_ocr: bool = Field(default=True, description="是否启用OCR文本识别")
    ocr_mode: Optional[OCRMode] = Field(
        default=OCRMode(value="prompt_ocr"),
        description="OCR模式（prompt_ocr: 仅文本识别; prompt_layout_all_en: 包含布局信息)"
    )
    
    # 验证器
    @field_validator('purpose', 'target_format', 'ocr_mode', mode='before')
    def coerce_value_models(cls, v):
        # 兼容纯字符串写法：自动包裹为 {"value": v}
        if isinstance(v, str):
            return {"value": v}
        return v


class ExtractionItem(BaseModel):
    """抽取项目"""
    extraction_class: str = Field(..., description="抽取类名（如 人物/事件）")
    extraction_text: str = Field(..., description="原文中的精确片段")
    char_interval: Optional[Dict[str, int]] = Field(None, description="字符位置区间")
    alignment_status: Optional[str] = Field(None, description="匹配状态")
    extraction_index: Optional[int] = Field(None, description="抽取索引")
    group_index: Optional[int] = Field(None, description="分组索引")
    description: Optional[str] = Field(None, description="描述")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="属性字典")
    
    @field_validator('attributes', mode='before')
    def ensure_attributes_dict(cls, v):
        """确保attributes始终是字典，即使收到None值"""
        if v is None:
            return {}
        return v


class FileExtractResponse(BaseModel):
    """信息抽取响应模型"""
    
    # 基础字段
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="处理状态: pending/processing/completed/failed")
    progress: Optional[float] = Field(None, ge=0.0, le=100.0, description="处理进度百分比")
    
    # 抽取结果
    document_id: Optional[str] = Field(None, description="文档ID")
    text_length: Optional[int] = Field(None, description="文本长度")
    extractions: List[ExtractionItem] = Field(default_factory=list, description="抽取结果列表")
    
    # 元数据
    processing_time: Optional[float] = Field(None, description="处理耗时（秒）")
    file_info: Optional[Dict[str, Any]] = Field(None, description="文件信息")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息（如果处理失败）")
    error_details: Optional[Dict[str, Any]] = Field(None, description="详细错误信息")
