"""
文件处理相关的数据模型
File processing related schemas
"""

from typing import Optional, List, Dict, Any, Literal
from config.constants import CONTENT_READING_OUTPUT_FORMATS
from pydantic import BaseModel, Field
from pydantic import field_validator, model_validator
import json


class ProcessingPurpose(BaseModel):
    """处理目的模型（当前仅用于日志，不参与分支）"""
    value: str = Field(..., description="处理目的值（当前仅日志用途）")
    
    @field_validator('value')
    def validate_purpose(cls, v):
        valid_values = ["content_reading"]
        if v not in valid_values:
            raise ValueError(f"处理目的必须是以下之一: {valid_values}")
        return v


class OutputFormat(BaseModel):
    """输出格式模型"""
    value: str = Field(..., description="输出格式值")
    
    @field_validator('value')
    def validate_format(cls, v):
        valid_content_reading_values = sorted(list(CONTENT_READING_OUTPUT_FORMATS))
        if v not in valid_content_reading_values:
            raise ValueError(f"输出格式必须是以下之一: {valid_content_reading_values}")
        return v


class TablePrecision(BaseModel):
    """表格精度模型"""
    value: int = Field(..., ge=0, le=20, description="表格精度值（0-20，数值越大精度越高）")
    
    @field_validator('value')
    def validate_precision(cls, v):
        if not (0 <= v <= 20):
            raise ValueError("表格精度必须在0到20之间")
        return v


class ChunkingStrategy(BaseModel):
    """分块策略模型 - 6个等级的分块方法"""
    value: str = Field(..., description="分块策略值")
    
    @field_validator('value')
    def validate_strategy(cls, v):
        valid_values = [
            # Auto: 自动选择
            "auto",
            # Level 1: Character Splitting
            "character_splitting",
            # Level 2: Recursive Character Text Splitting  
            "recursive_character_splitting",
            # Level 3: Document Specific Splitting
            "document_specific_splitting",
            # Level 4: Semantic Splitting
            "semantic_splitting", 
            # Level 5: Agentic Splitting
            "agentic_splitting",
            # Bonus Level: Alternative Representation Chunking
            "alternative_representation_chunking",
            # Level 6: Custom Delimiter Splitting
            "custom_delimiter_splitting",
            # Level 6+: Custom Delimiter Splitting with Table Preservation
            "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone",
        ]
        if v not in valid_values:
            raise ValueError(f"分块策略必须是以下之一: {valid_values}")
        return v


 


class RecursiveSplittingConfig(BaseModel):
    """Level 2: 递归字符分块配置"""
    separators: List[str] = Field(
        default=["\n\n", "\n", ". ", ", ", " "],
        description="分隔符列表，按序退化分割"
    )
    keep_separator: bool = Field(
        default=True,
        description="是否保留分隔符到相邻文本"
    )


class DocumentSpecificConfig(BaseModel):
    """Level 3: 文档特定分块配置"""
    document_type: Literal["pdf", "markdown", "md", "python", "py", "html"] = Field(
        ..., description="文档类型"
    )
    preserve_headers: bool = Field(default=True, description="是否保留标题（Markdown/HTML）")
    preserve_code_blocks: bool = Field(default=True, description="是否保留代码块（Markdown/HTML/Python注释块）")
    preserve_lists: bool = Field(default=True, description="是否保留列表结构（Markdown/HTML）")


class SemanticSplittingConfig(BaseModel):
    """Level 4: 语义分块配置（基于嵌入）"""
    embedding_model: Optional[str] = Field(
        default=None, description="覆盖默认嵌入模型名（不填则使用系统配置）"
    )
    similarity_threshold: float = Field(
        default=0.25, ge=0.0, le=1.0, description="相邻块相似度阈值，低于该值将切分"
    )
    buffer_size: int = Field(
        default=1, ge=1, le=5, description="句子组合窗口大小，用于减少噪音并增强语义连贯性"
    )
    min_chunk_size: Optional[int] = Field(
        default=None, ge=1, description="可选：每块最小字符数（不填则使用全局 chunk_size 逻辑）"
    )
    max_chunk_size: Optional[int] = Field(
        default=None, ge=1, description="可选：每块最大字符数（不填则使用全局 chunk_size 逻辑）"
    )


class AgenticSplittingConfig(BaseModel):
    """Level 5: 智能代理分块配置（实验性）"""
    llm_model: Optional[str] = Field(default=None, description="覆盖默认文本模型名")
    chunking_prompt: Optional[str] = Field(
        default=None, description="自定义分块提示词，不填则使用内置系统提示词"
    )
    max_tokens_per_chunk: Optional[int] = Field(
        default=2048, ge=1, description="单次调用允许的最大 tokens（影响返回 JSON 的容量）"
    )
    preserve_context: bool = Field(
        default=True, description="是否在后处理阶段保留上下文（通过 chunk_overlap 实现）"
    )
    enable_thinking: bool = Field(
        default=False, description="是否启用模型的思考模式（经由 extra_body.chat_template_kwargs 传递）"
    )
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="生成温度")
    extra_body: Optional[Dict[str, Any]] = Field(
        default=None, description="下传给底层聊天接口的 extra_body 扩展"
    )


class AlternativeRepresentationConfig(BaseModel):
    """Bonus: 替代表示分块配置（衍生表示/索引）"""
    representation_types: List[str] = Field(
        default_factory=lambda: ["outline", "code_blocks", "tables"],
        description="衍生表示类型集合（示例：outline, code_blocks, tables, summary, keywords）",
    )
    indexing_strategy: str = Field(default="hybrid", description="索引策略（例如: dense/sparse/hybrid）")
    retrieval_optimized: bool = Field(default=True, description="是否为检索优化存储这些衍生表示")
    include_outline: bool = Field(default=True, description="是否抽取大纲（Markdown标题等）")
    include_code_blocks: bool = Field(default=True, description="是否抽取代码块")
    include_tables: bool = Field(default=True, description="是否抽取表格")


class CustomDelimiterConfig(BaseModel):
    """Level 6: 自定义分隔符分块配置"""
    delimiter: str = Field(
        default="。",
        description="自定义分隔符，支持中文字符和转义字符（\\n, \\t, \\r等）"
    )


class ChunkingConfig(BaseModel):
    """分块配置模型 - 支持6个等级的分块策略配置"""

    # Level 1: Character Splitting 配置
    character_splitting_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Level 1: 字符级分块配置"
    )

    # Level 2: Recursive Character Text Splitting 配置
    recursive_splitting_config: Optional[RecursiveSplittingConfig] = Field(
        default=None,
        description="Level 2: 递归字符分块配置，包含分隔符列表"
    )

    # Level 3: Document Specific Splitting 配置
    document_specific_config: Optional[DocumentSpecificConfig] = Field(
        default=None,
        description="Level 3: 文档特定分块配置，支持PDF、Python、Markdown等"
    )

    # Level 4: Semantic Splitting 配置
    semantic_splitting_config: Optional[SemanticSplittingConfig] = Field(
        default=None,
        description="Level 4: 语义分块配置，基于嵌入的分块"
    )

    # Level 5: Agentic Splitting 配置
    agentic_splitting_config: Optional[AgenticSplittingConfig] = Field(
        default=None,
        description="Level 5: 智能代理分块配置，实验性方法"
    )

    # Level 6: Custom Delimiter Splitting 配置
    custom_delimiter_config: Optional[CustomDelimiterConfig] = Field(
        default=None,
        description="Level 6: 自定义分隔符分块配置"
    )

    # Bonus Level: Alternative Representation Chunking 配置
    alternative_representation_config: Optional[AlternativeRepresentationConfig] = Field(
        default=None,
        description="Bonus Level: 替代表示分块配置，用于检索和索引"
    )


class ModelProcessingConfig(BaseModel):
    """模型处理配置（未实现，预留：总结/改写/抽取等）"""
    enable: bool = Field(default=False, description="是否启用模型处理（未实现）")
    prompt: Optional[str] = Field(default=None, description="自定义提示词（未实现）")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词（未实现）")
    model_name: Optional[str] = Field(default=None, description="模型名称（未实现）")
    temperature: Optional[float] = Field(default=0.3, ge=0.0, le=2.0, description="采样温度（未实现）")
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="核采样top_p（未实现）")
    max_tokens: Optional[int] = Field(default=1024, ge=1, description="最大输出token数（未实现）")


# ---------------- LangExtract 配置（必填） ----------------
class LXExtractionItem(BaseModel):
    extraction_class: str = Field(..., description="抽取类名（如 人物/事件）")
    extraction_text: str = Field(..., description="原文中的精确片段")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="属性字典")


class LXExampleData(BaseModel):
    text: str = Field(..., description="示例原文片段")
    extractions: List[LXExtractionItem] = Field(default_factory=list, description="在该示例中的抽取标签列表")


class LangExtractConfig(BaseModel):
    prompt: str = Field(..., description="抽取任务的指令")
    # 命名沿用“extractions”，但其结构为 few-shot 示例集合
    extractions: List[LXExampleData] = Field(default_factory=list, description="few-shot 示例集合")


class OCRMode(BaseModel):
    """OCR模式模型"""
    value: str = Field(..., description="OCR模式值")
    
    @field_validator('value')
    def validate_ocr_mode(cls, v):
        valid_values = ["prompt_layout_all_en", "prompt_layout_only_en", "prompt_ocr", "prompt_grounding_ocr"]
        if v not in valid_values:
            raise ValueError(f"OCR模式必须是以下之一: {valid_values}")
        return v


class FileProcessRequest(BaseModel):
    """文件处理请求模型"""
    
    # 必需参数
    task_id: str = Field(..., description="任务ID，用于跟踪处理进度")
    purpose: ProcessingPurpose = Field(..., description="读取文件的目的")
    target_format: OutputFormat = Field(..., description="目标输出格式")
    # 信息抽取开关与配置（与现有风格一致：enable_xxx + xxx_config）
    enable_extract: bool = Field(default=False, description="是否启用基于 LangExtract 的信息抽取")
    extract_config: Optional[LangExtractConfig] = Field(
        default=None,
        description="信息抽取配置（含 prompt 与 extractions）",
    )
    
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
    
    # 分块相关参数
    enable_chunking: bool = Field(default=False, description="是否启用文本分块")
    chunking_strategy: Optional[ChunkingStrategy] = Field(
        default=ChunkingStrategy(value="auto"), 
        description="分块策略（auto 自动选择）"
    )
    chunk_size: Optional[int] = Field(
        default=1000, 
        ge=100, 
        le=99999999, 
        description="分块大小（字符数）"
    )
    chunk_overlap: Optional[int] = Field(
        default=200, 
        ge=0, 
        le=1000, 
        description="分块重叠大小（字符数）"
    )
    # 高级分块配置
    chunking_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="分块策略的具体配置参数"
    )
    
    # 多文件处理参数
    enable_multi_file_summary: bool = Field(
        default=False, 
        description="是否需要对多文件进行总结"
    )
    summary_length: Optional[int] = Field(
        default=500, 
        ge=100, 
        le=2000, 
        description="总结长度（字符数）"
    )
    summary_focus: Optional[List[str]] = Field(
        default=["main_points", "key_findings", "recommendations"], 
        description="总结重点关注的方面"
    )


    # 仅针对 summary 的响应控制
    summary_return_top_k: Optional[int] = Field(
        default=None,
        ge=1,
        description="返回前K条要点/段落（未实现）"
    )

    # 自定义参数（灵活扩展）
    custom_parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="自定义参数，可以接收任何额外的参数"
    )
    
    # 验证器
    @field_validator('purpose', 'target_format', 'chunking_strategy', 'ocr_mode', mode='before')
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

    @model_validator(mode='after')
    def validate_chunk_parameters(self):
        if self.chunk_size is not None and self.chunk_overlap is not None:
            if self.chunk_overlap >= self.chunk_size:
                raise ValueError("分块重叠大小不能大于或等于分块大小")
        return self
    
    @field_validator('custom_parameters')
    def validate_custom_parameters(cls, v):
        # 确保自定义参数可以被JSON序列化
        try:
            json.dumps(v)
        except (TypeError, ValueError):
            raise ValueError("自定义参数必须是可以JSON序列化的")
        return v

    @model_validator(mode='after')
    def validate_extract_config(self):
        # 开启时必须有配置
        if self.enable_extract and self.extract_config is None:
            raise ValueError("已开启 enable_extract，但未提供 extract_config")
        return self


class ProcessingOptions(BaseModel):
    """处理选项的详细配置（未实现，预留）"""
    
    # 输出选项
    output_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="输出格式的具体选项"
    )
    
    # 分块选项
    chunking_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="分块的具体配置选项"
    )
    
    # 清理选项
    cleaning_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="数据清理的具体配置选项"
    )
    
    # 总结选项
    summary_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="多文件总结的具体配置选项"
    )


class FileProcessResponse(BaseModel):
    """文件处理响应模型"""
    
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="处理状态: pending/processing/completed/failed")
    progress: Optional[float] = Field(None, ge=0.0, le=100.0, description="处理进度百分比")
    
    # 处理结果
    result_url: Optional[str] = Field(None, description="结果文件下载URL")
    result_data: Optional[Dict[str, Any]] = Field(None, description="直接返回的结果数据")
    
    # 元数据
    processing_time: Optional[float] = Field(None, description="处理耗时（秒）")
    file_info: Optional[Dict[str, Any]] = Field(None, description="文件信息")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息（如果处理失败）")
    error_details: Optional[Dict[str, Any]] = Field(None, description="详细错误信息")


# 示例JSON结构
EXAMPLE_REQUEST = {
    "task_id": "task_20241201_001",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "markdown"},
    "table_precision": {"value": 15},
    "enable_chunking": True,
    "chunking_strategy": {"value": "auto"},
    "chunk_size": 1500,
    "chunk_overlap": 200,
    "chunking_config": {
        "semantic_splitting_config": {
            "embedding_model": "text-embedding-ada-002",
            "similarity_threshold": 0.8,
            "min_chunk_size": 100,
            "max_chunk_size": 2000
        }
    },
    "enable_multi_file_summary": True,
    "summary_length": 800,
    "summary_focus": ["main_points", "key_findings", "recommendations"],
    "model_processing": {
        "enable": True,
        "prompt": "请用5条要点总结本文档的关键信息",
        "model_name": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 512
    }
} 