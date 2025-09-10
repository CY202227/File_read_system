# 文件处理系统API文档

本文档详细介绍了文件处理系统的所有API接口、参数及其功能。

## 目录

- [上传接口](#上传接口)
  - [文件流上传](#文件流上传)
  - [文本内容上传](#文本内容上传)
  - [文件路径上传](#文件路径上传)
- [处理接口](#处理接口)
  - [文件处理](#文件处理)
  - [文件读取](#文件读取)
  - [文件切片](#文件切片)
  - [文件总结](#文件总结)
  - [信息抽取](#信息抽取)

## 上传接口

### 文件流上传

**接口**：`POST /upload/stream`

**功能**：通过文件流上传单个或多个文件

**参数**：

- **files**：要上传的文件列表（支持单个或多个文件）
- **task_id**：可选的任务ID（如果之前上传过已经有了id的话），如果不提供将自动生成
- **priority**：任务优先级 (1=低, 2=普通, 3=高, 4=紧急)

**返回**：

```json
{
  "task_id": "string",
  "total_files": 0,
  "successful_uploads": 0,
  "failed_uploads": 0,
  "files": [
    {
      "file_uuid": "string",
      "original_filename": "string",
      "file_path": "string",
      "file_size": 0,
      "status": "string",
      "error_message": "string"
    }
  ],
  "message": "string"
}
```

### 文本内容上传

**接口**：`POST /upload/text`

**功能**：上传纯文本内容

**参数**：

- **content**：纯文本内容
- **task_id**：可选的任务ID，如果不提供将自动生成
- **priority**：任务优先级 (1=低, 2=普通, 3=高, 4=紧急)
- **auto_detect**：是否自动检测文本格式，默认为true
- **extension**：手动模式下的文件扩展名（仅在auto_detect=false时需要，如：txt, md, html）

**返回**：与文件流上传相同

**调用示例**：
```json
{
  "content": "# 这是Markdown内容",
  "auto_detect": true,
  "priority": "2"
}
```

### 文件路径上传

**接口**：`POST /upload/file`

**功能**：通过文件路径上传单个或多个文件

**参数**：

- **file_paths**：文件路径列表（支持单个或多个文件）
- **task_id**：可选的任务ID，如果不提供将自动生成

**返回**：与文件流上传相同

**调用示例**：
```json
{
  "file_paths": ["/path/to/file1.pdf"],
  "task_id": "task_20241201_001"
}
```

## 处理接口

### 文件处理

**接口**：`POST /file/process`

**功能**：提交文件处理任务（同步：内部队列顺序执行，完成后直接返回结果）

**基础参数**：

- **task_id**：任务ID，用于跟踪处理进度
- **purpose**：处理目的，目前支持 "content_reading"
- **target_format**：目标输出格式，支持多种格式如 "plain_text", "markdown" 等

**OCR相关参数**：

- **enable_ocr**：是否启用OCR文本识别，默认为true
- **ocr_mode**：OCR模式，可选值：
  - "prompt_ocr"：仅文本识别（默认）
  - "prompt_layout_all_en"：包含布局信息
  - "prompt_layout_only_en"：仅包含布局信息
  - "prompt_grounding_ocr"：基于图像理解的OCR

**表格处理参数**：

- **table_precision**：读取表格的精度，范围0-20，数值越大精度越高，默认为10

**分块相关参数**：

- **enable_chunking**：是否启用文本分块，默认为false
- **chunking_strategy**：分块策略，默认为"auto"，可选值包括：
  - "auto"：自动选择
  - "character_splitting"：字符级分块
  - "recursive_character_splitting"：递归字符分块
  - "document_specific_splitting"：文档特定分块
  - "semantic_splitting"：语义分块
  - "agentic_splitting"：智能代理分块
  - "alternative_representation_chunking"：替代表示分块
  - "custom_delimiter_splitting"：自定义分隔符分块
  - "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone"：带表格保留的自定义分隔符分块
- **chunk_size**：分块大小（字符数），范围100-99,999,999，默认1000
- **chunk_overlap**：分块重叠大小（字符数），范围0-1000，默认200
- **chunking_config**：分块策略的具体配置参数

**多文件处理参数**：

- **enable_multi_file_summary**：是否需要对多文件进行总结，默认为false
- **summary_length**：总结长度（字符数），范围100-2000，默认500
- **summary_focus**：总结重点关注的方面，默认为["main_points", "key_findings", "recommendations"]
- **summary_return_top_k**：返回前K条要点/段落

**信息抽取参数**：

- **enable_extract**：是否启用基于LangExtract的信息抽取，默认为false
- **extract_config**：信息抽取配置，包含prompt和extractions示例

**自定义参数**：

- **custom_parameters**：自定义参数，可以接收任何额外的参数

**调用示例**：

1. 基础文件读取（plain_text）
```json
{
  "task_id": "task_20241201_001",
  "purpose": {"value": "content_reading"},
  "target_format": {"value": "plain_text"}
}
```

2. 启用分块处理的调用示例
```json
{
  "task_id": "task_20241201_003",
  "purpose": {"value": "content_reading"},
  "target_format": {"value": "plain_text"},
  "enable_chunking": true,
  "chunking_strategy": {"value": "recursive_character_splitting"},
  "chunk_size": 1500,
  "chunk_overlap": 200,
  "chunking_config": {
    "recursive_splitting_config": {
      "separators": ["\n\n", "\n", "! ", "? ", " ", ""],
      "keep_separator": true
    }
  }
}
```

3. 启用文件总结的调用示例
```json
{
  "task_id": "task_20241201_004",
  "purpose": {"value": "content_reading"},
  "target_format": {"value": "markdown"},
  "enable_multi_file_summary": true,
  "summary_length": 800,
  "summary_focus": ["main_points", "key_findings", "recommendations"]
}
```

### 文件读取

**接口**：`POST /file/read`

**功能**：文件内容读取接口（仅执行文件读取步骤）

**参数**：

- **task_id**：任务ID，用于跟踪处理进度
- **purpose**：读取文件的目的，目前支持 "content_reading"
- **target_format**：目标输出格式
- **enable_ocr**：是否启用OCR文本识别，默认为true
- **ocr_mode**：OCR模式，同文件处理接口
- **table_precision**：读取表格的精度，范围0-20，默认为10

**调用示例**：
```json
{
  "task_id": "task_20241201_001",
  "purpose": {"value": "content_reading"},
  "target_format": {"value": "markdown"},
  "table_precision": {"value": 10}
}
```

### 文件切片

**接口**：`POST /file/chunk`

**功能**：文件切片接口（执行文件切片步骤，如需会自动调用读取）

**参数**：

- **task_id**：任务ID，用于跟踪处理进度
- **chunking_strategy**：分块策略，默认为"auto"
- **chunk_size**：分块大小（字符数），范围100-99,999,999，默认1000
- **chunk_overlap**：分块重叠大小（字符数），范围0-1000，默认200
- **chunking_config**：分块策略的具体配置参数

**`chunking_config` 配置选项**：

#### 递归字符分块配置 (recursive_splitting_config)

- **separators**：分隔符列表，按序退化分割，默认为["\n\n", "\n", ". ", ", ", " "]
- **keep_separator**：是否保留分隔符到相邻文本，默认为true

#### 文档特定分块配置 (document_specific_config)

- **document_type**：文档类型，支持 "pdf", "markdown", "md", "python", "py", "html"
- **preserve_headers**：是否保留标题（Markdown/HTML），默认为true
- **preserve_code_blocks**：是否保留代码块（Markdown/HTML/Python注释块），默认为true
- **preserve_lists**：是否保留列表结构（Markdown/HTML），默认为true

#### 语义分块配置 (semantic_splitting_config)

**embedding_model**：覆盖默认嵌入模型名（不填则使用系统配置）

**similarity_threshold**：相邻块相似度阈值，低于该值将切分，范围0.0-1.0，默认0.25

**buffer_size**：句子组合窗口大小，用于减少噪音并增强语义连贯性，范围1-5，默认1

**min_chunk_size**：每块最小字符数（不填则使用全局chunk_size逻辑）

**max_chunk_size**：每块最大字符数（不填则使用全局chunk_size逻辑）

#### 智能代理分块配置 (agentic_splitting_config)

- **llm_model**：覆盖默认文本模型名
- **chunking_prompt**：自定义分块提示词，不填则使用内置系统提示词
- **max_tokens_per_chunk**：单次调用允许的最大tokens（影响返回JSON的容量），默认2048
- **preserve_context**：是否在后处理阶段保留上下文（通过chunk_overlap实现），默认为true
- **enable_thinking**：是否启用模型的思考模式，默认为false
- **temperature**：生成温度，范围0.0-2.0，默认0.0
- **extra_body**：下传给底层聊天接口的extra_body扩展

#### 替代表示分块配置 (alternative_representation_config)

- **representation_types**：衍生表示类型集合，默认为["outline", "code_blocks", "tables"]
- **indexing_strategy**：索引策略，默认为"hybrid"
- **retrieval_optimized**：是否为检索优化存储这些衍生表示，默认为true
- **include_outline**：是否抽取大纲（Markdown标题等），默认为true
- **include_code_blocks**：是否抽取代码块，默认为true
- **include_tables**：是否抽取表格，默认为true

#### 自定义分隔符分块配置 (custom_delimiter_config)

- **delimiter**：自定义分隔符，支持中文字符和转义字符（\n, \t, \r等），默认为"。"

**调用示例**：

1. 最简单的切片
```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "character_splitting"},
  "chunk_size": 1000,
  "chunk_overlap": 10
}

```

2. 按段落切分（保持文档结构）
```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "recursive_character_splitting"},
  "chunk_size": 1500,
  "chunk_overlap": 200
}
```

3. 语义切分（最智能但最慢）
```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "semantic_splitting"},
  "chunk_size": 1500,
  "chunk_overlap": 200,
  "chunking_config": {
    "semantic_splitting_config": {
      "embedding_model": "text-embedding-ada-002",
      "similarity_threshold": 0.8,
      "min_chunk_size": 100,
      "max_chunk_size": 2000
    }
  }
}
```

4. 处理包含表格的文档
```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone"},
  "chunk_size": 2000,
  "chunk_overlap": 300,
  "chunking_config": {
    "custom_delimiter_config": {
      "delimiter": "\n\n"
    }
  }
}
```

### 文件总结

**接口**：`POST /file/summarize`

**功能**：文件总结接口（执行文件总结步骤，如需会自动调用读取）

**参数**：

**task_id**：任务ID，用于跟踪处理进度

**summary_length**：总结长度（字符数），范围100-2000，默认500

**summary_focus**：总结重点关注的方面，默认为["main_points", "key_findings", "recommendations"]

**summary_return_top_k**：返回前K条要点/段落

**调用示例**：
```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "summary_length": 800,
  "summary_focus": ["main_points", "key_findings", "recommendations"],
  "summary_return_top_k": 5
}
```

### 信息抽取

**接口**：`POST /file/extract`

**功能**：信息抽取接口（基于LangExtract执行信息抽取，如需会自动调用读取）

**参数**：

- **task_id**：任务ID，用于跟踪处理进度
- **extract_config**：信息抽取配置（必需），包含以下字段：
  - **prompt**：抽取任务的指令
  - **extractions**：few-shot示例集合，每个示例包含：
    - **text**：示例原文片段
    - **extractions**：在该示例中的抽取标签列表，每个标签包含：
      - **extraction_class**：抽取类名（如人物/事件）
      - **extraction_text**：原文中的精确片段
      - **attributes**：属性字典
- **purpose**：读取文件的目的，默认为"content_reading"
- **target_format**：目标输出格式，默认为"plain_text"
- **enable_ocr**：是否启用OCR文本识别，默认为true
- **ocr_mode**：OCR模式，同文件处理接口

**调用示例**：
```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "extract_config": {
    "prompt": "请从文本中提取人物与事件，必须返回原文精确片段。",
    "extractions": [
      {
        "text": "示例原文片段：胡文容是市政协党组书记、主席。",
        "extractions": [
          {
            "extraction_class": "人物", 
            "extraction_text": "胡文容", 
            "attributes": {"职务": "市政协党组书记、主席"}
          }
        ]
      }
    ]
  }
}
```