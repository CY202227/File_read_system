# 文件处理API使用示例（对齐当前实现）

## 概述

本文档展示了如何使用文件处理系统的JSON参数结构。所有参数都使用BaseModel形式，提供更好的类型安全和验证。

接口路径：除“文件上传”路由外，文件处理主入口为 `POST /api/v1/file/process`。

## 文件上传功能

### 纯文本上传

系统支持直接上传纯文本内容，支持自动格式检测和手动指定格式两种模式。

#### 端点
- `POST /api/v1/api/upload/text`

#### 参数
- `content`: 纯文本内容（必需）
- `task_id`: 可选的任务ID，不提供则自动生成
- `priority`: 任务优先级（1=低, 2=普通, 3=高, 4=紧急）
- `auto_detect`: 格式检测模式
  - `"auto"`: 自动检测文本格式（HTML、Markdown、纯文本等）
  - `"manual"`: 使用指定的扩展名（需要提供extension参数）
- `extension`: 手动模式下的文件扩展名（仅在auto_detect='manual'时需要）

#### 格式检测规则
- **HTML**: 检测到HTML标签（如 `<html>`, `<head>`, `<body>`, `<div>`, `<p>` 等）
- **Markdown**: 检测到Markdown语法（标题、粗体、斜体、链接、列表等）
- **纯文本**: 其他情况

#### 使用示例

**自动检测格式（推荐）**
```bash
curl -X POST "http://localhost:5015/api/v1/api/upload/text" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# 这是Markdown内容",
    "auto_detect": true
  }'
```

**手动指定格式**
```bash
curl -X POST "http://localhost:5015/api/v1/api/upload/text" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "这是纯文本内容",
    "auto_detect": false,
    "extension": "txt"
  }'
```

**HTML内容自动检测**
```bash
curl -X POST "http://localhost:5015/api/v1/api/upload/text" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "<!DOCTYPE html><html><body><h1>标题</h1></body></html>",
    "auto_detect": true
  }'
```

**手动指定HTML格式**
```bash
curl -X POST "http://localhost:5015/api/v1/api/upload/text" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "<div>HTML内容</div>",
    "auto_detect": false,
    "extension": "html"
  }'
```

**指定优先级**
```bash
curl -X POST "http://localhost:5015/api/v1/api/upload/text" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# 标题\n这是一个 Markdown 文档\n- 列表项1\n- 列表项2",
    "priority": "3",
    "auto_detect": true
  }'
```

#### 响应格式
```json
{
    "task_id": "uuid-string",
    "total_files": 1,
    "successful_uploads": 1,
    "failed_uploads": 0,
    "files": [
        {
            "file_uuid": "uuid-string",
            "original_filename": "text_uuid-string.md",
            "file_path": "uploads/task-id/uuid-string.md",
            "file_size": 1234,
            "status": "success",
            "error_message": null
        }
    ],
    "message": "文本内容上传成功，文件名: text_uuid-string.md"
}
```

## 基本参数结构

### 必需参数

- `task_id`: 任务ID
- `purpose`: 读取文件的目的（当前仅接收 `content_reading`，仅日志用途）
- `target_format`: 目标输出格式（`plain_text | markdown | dataframe`）

### 可选参数

- `table_precision`: 表格精度（DataFrame读取显示精度）
- `enable_chunking`: 是否启用文本分块
- `chunking_strategy`: 分块策略（见下）
- `chunk_size` / `chunk_overlap`: 分块尺寸配置
- `chunking_config`: 各策略细化配置（见下）
- `enable_multi_file_summary`: 是否进行摘要
- `summary_length` / `summary_focus` / `summary_return_top_k`
- `custom_parameters`: 自定义参数（透传占位）

## 使用示例

### 1. 基础文件读取（plain_text）

```json
{
    "task_id": "task_20241201_001",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "plain_text"}
}
```

### 2. DataFrame 读取

```json
{
    "task_id": "task_20241201_002",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "dataframe"},
    "table_precision": {"value": 12}
}
```

### 3. 文本分块处理（返回主体按 target_format；chunking 附带在 result_data.chunking）

#### 3.1 Level 1: 字符级分块

```json
{
    "task_id": "task_20241201_003a",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "plain_text"},
    "enable_chunking": true,
    "chunking_strategy": {"value": "character_splitting"},
    "chunk_size": 1000,
    "chunk_overlap": 100
}
```

#### 3.2 Level 2: 递归字符分块

```json
{
    "task_id": "task_20241201_003b",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "plain_text"},
    "enable_chunking": true,
    "chunking_strategy": {"value": "recursive_character_splitting"},
    "chunk_size": 1500,
    "chunk_overlap": 200,
    "chunking_config": {
        "recursive_splitting_config": {
            "separators": ["\n\n", "\n", ". ", "! ", "? ", " ", ""],
            "keep_separator": true
        }
    }
}
```

#### 3.3 Level 3: 文档特定分块

```json
{
    "task_id": "task_20241201_003c",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "plain_text"},
    "enable_chunking": true,
    "chunking_strategy": {"value": "document_specific_splitting"},
    "chunk_size": 2000,
    "chunk_overlap": 300,
    "chunking_config": {
        "document_specific_config": {
            "document_type": "markdown",
            "preserve_headers": true,
            "preserve_code_blocks": true,
            "preserve_lists": true
        }
    }
}
```

#### 3.4 Level 4: 语义分块

```json
{
    "task_id": "task_20241201_003d",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "plain_text"},
    "enable_chunking": true,
    "chunking_strategy": {"value": "auto"},
    "chunk_size": 1500,
    "chunk_overlap": 200,
    "chunking_config": {
        "semantic_splitting_config": {
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "similarity_threshold": 0.8,
            "min_chunk_size": 100,
            "max_chunk_size": 2000
        }
    }
}
```

#### 3.5 Level 5: 智能代理分块

```json
{
    "task_id": "task_20241201_003e",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "plain_text"},
    "enable_chunking": true,
    "chunking_strategy": {"value": "agentic_splitting"},
    "chunk_size": 2000,
    "chunk_overlap": 300,
    "chunking_config": {
        "agentic_splitting_config": {
            "llm_model": "gpt-3.5-turbo",
            "chunking_prompt": "将以下文本按照语义完整性进行分块",
            "max_tokens_per_chunk": 2000,
            "preserve_context": true
        }
    }
}
```

#### 3.6 Bonus Level: 替代表示分块

```json
{
    "task_id": "task_20241201_003f",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "chunks"},
    "content_return_format": {"value": "structured"},
    "enable_chunking": true,
    "chunking_strategy": {"value": "alternative_representation_chunking"},
    "chunk_size": 1500,
    "chunk_overlap": 200,
    "chunking_config": {
        "alternative_representation_config": {
            "representation_types": ["summary", "keywords", "entities", "sentiment"],
            "indexing_strategy": "hybrid",
            "retrieval_optimized": true
        }
    }
}
```

### 3.6 Level 6: 自定义分隔符分块

```json
{
    "task_id": "task_20241201_003g",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "plain_text"},
    "enable_chunking": true,
    "chunking_strategy": {"value": "custom_delimiter_splitting"},
    "chunk_size": 1000,
    "chunk_overlap": 100,
    "chunking_config": {
        "custom_delimiter_config": {
            "delimiter": "——END——"
        }
    }
}
```

### 4. 多文件总结

```json
{
    "task_id": "task_20241201_004",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "plain_text"},
    "enable_multi_file_summary": true,
    "summary_length": 800,
    "summary_focus": ["main_points", "key_findings", "recommendations"]
}
```

### 4.1 Summary 响应控制（Top-K）

```json
{
    "task_id": "task_20241201_004_stream",
    "purpose": "content_reading",
    "target_format": "plain_text",
    "summary_return_top_k": 5,
    "enable_multi_file_summary": true
}
```

（已移除未实现项示例：数据清理、OCR、格式转换等）

### 5. 信息抽取（基于 LangExtract）

```json
{
  "task_id": "task_20241201_005",
  "purpose": {"value": "content_reading"},
  "target_format": {"value": "plain_text"},
  "enable_extract": true,
  "extract_config": {
    "prompt": "请从文本中提取人物与事件，必须返回原文精确片段。",
    "extractions": [
      {
        "text": "示例原文片段……",
        "extractions": [
          {"extraction_class": "人物", "extraction_text": "胡文容", "attributes": {"职务": "市政协党组书记、主席"}}
        ]
      }
    ]
  }
}
```

响应体中的 `result_data.extraction` 将包含：

```json
{
  "document_id": "doc_xxx",
  "text_length": 1234,
  "extractions": [
    {
      "extraction_class": "人物",
      "extraction_text": "胡文容",
      "char_interval": {"start_pos": 10, "end_pos": 13},
      "alignment_status": "match_exact",
      "extraction_index": 1,
      "group_index": 0,
      "description": null,
      "attributes": {"职务": "市政协党组书记、主席"}
    }
  ]
}
```

## 参数说明

### ProcessingPurpose (处理目的)

- `content_reading`: 读取文件内容

### OutputFormat (输出格式)

- `plain_text` / `markdown` / `dataframe`

### ContentReturnFormat (内容返回格式)

- `dataframe`: 结构化数据（表格）
- `plain_text`: 纯文本
- markdown: Markdown

### TablePrecision (表格精度)

- 范围：0-20
- 数值越大精度越高，处理越慢
- 建议值：10-15

### ChunkingStrategy (分块策略) - 6个等级

[分块策略详情](https://github.com/FullStackRetrieval-com/RetrievalTutorials/blob/main/tutorials/LevelsOfTextSplitting/5_Levels_Of_Text_Splitting.ipynb)

#### Level 1: Character Splitting (字符级分块)

- `character_splitting`: 简单的静态字符分块
- 适用场景：快速处理，对语义要求不高

#### Level 2: Recursive Character Text Splitting (递归字符分块)

- `recursive_character_splitting`: 基于分隔符列表的递归分块
- 配置参数：separators (分隔符列表), keep_separator (是否保留分隔符)

#### Level 3: Document Specific Splitting (文档特定分块)

- `document_specific_splitting`: 针对不同文档类型的分块方法
- 支持：PDF、Python、Markdown、HTML等
- 配置参数：document_type, preserve_headers, preserve_code_blocks等

#### Level 4: Semantic Splitting (语义分块)

- `semantic_splitting`: 基于嵌入的语义感知分块
- 配置参数：embedding_model, similarity_threshold, buffer_size, min_chunk_size, max_chunk_size
- `buffer_size`: 句子组合窗口大小（默认1），用于减少噪音并增强语义连贯性

#### Level 5: Agentic Splitting (智能代理分块)

- `agentic_splitting`: 实验性的智能代理分块方法
- 适用场景：token成本趋近于0时
- 配置参数：llm_model, chunking_prompt, max_tokens_per_chunk

#### Bonus Level: Alternative Representation Chunking (替代表示分块)

- #### Level 6: Custom Delimiter Splitting（自定义分隔符）

  - `custom_delimiter_splitting`：按 `custom_delimiter_config.delimiter` 切分
  - 配置参数：`custom_delimiter_config.delimiter`（字符串，必填）

#### Level 6+: Custom Delimiter Splitting with Table Preservation（自定义分隔符切分并保持表格完整）

- `custom_delimiter_splitting_with_chunk_size_and_leave_table_alone`：按分隔符切分，但保持markdown表格完整
- 配置参数：`custom_delimiter_config.delimiter`（字符串，必填）
- 特点：

  - 自动识别并保持 markdown 表格完整
  - 其他文本按分隔符切分后，进行智能合并，确保每块尽可能接近 chunk_size
  - 适用于包含表格的文档，确保表格结构不被破坏
- 表格识别：包含 `|` 的行 + 分隔符行（如 `|-----|-----|`）+ 数据行
- 智能合并：将相邻段落合并，直到接近目标大小
- `alternative_representation_chunking`: 用于检索和索引的替代表示
- 配置参数：representation_types, indexing_strategy, retrieval_optimized

### Summary 响应控制

- `summary_return_top_k` (int): 返回前 K 条要点；当无内容时短路为空

### 兼容纯字符串输入

- 可将 `purpose`、`target_format`、`content_return_format`、`cleaning_level`、`chunking_strategy` 直接传为字符串
- 服务端会自动包裹为 `{ "value": "..." }` 后再校验

## 错误处理

当参数验证失败时，系统会返回详细的错误信息：

```json
{
    "error": "Validation error",
    "detail": "处理目的必须是以下之一: ['format_conversion', 'content_reading', 'both']",
    "task_id": "task_20241201_001"
}
```

## 最佳实践

1. **任务ID**: 使用有意义的ID，便于跟踪和调试
2. **精度设置**: 根据文件大小和性能要求选择合适的表格精度
3. **分块大小**: 根据后续处理需求设置合适的分块大小
4. **自定义参数**: 充分利用custom_parameters字段进行扩展
5. **错误处理**: 始终检查响应状态和错误信息

## 分块策略选择指南

### 根据使用场景选择分块策略

具体实现见：[分块策略](https://github.com/FullStackRetrieval-com/RetrievalTutorials/blob/main/tutorials/LevelsOfTextSplitting/5_Levels_Of_Text_Splitting.ipynb)

1. **快速处理，对语义要求不高**

   - 推荐：Level 1 (character_splitting)
   - 特点：速度快，资源消耗少
2. **需要保持文本结构**

   - 推荐：Level 2 (recursive_character_splitting)
   - 特点：基于分隔符，保持段落和句子结构
3. **处理特定格式文档**

   - 推荐：Level 3 (document_specific_splitting)
   - 特点：针对PDF、Markdown、代码等特定格式优化
4. **需要语义完整性**

   - 推荐：Level 4 (semantic_splitting)
   - 特点：基于语义相似度，保持语义连贯性
5. **实验性高级分块**

   - 推荐：Level 5 (agentic_splitting)
   - 特点：使用LLM进行智能分块，成本较高
6. **用于检索和索引**

   - 推荐：Bonus Level (alternative_representation_chunking)
   - 特点：生成多种表示形式，优化检索效果
7. **处理包含表格的文档**

   - 推荐：Level 6+ (custom_delimiter_splitting_with_chunk_size_and_leave_table_alone)
   - 特点：保持表格完整，其他文本按分隔符和智能合并处理

## 性能考虑

- **Level 1-2**: 处理速度快，资源消耗少
- **Level 3**: 中等复杂度，适合特定文档类型
- **Level 4**: 需要计算嵌入，速度较慢但质量高
- **Level 5**: 需要调用LLM，成本最高但效果最好
- **Level 6+**: 表格识别和智能合并，适合包含表格的文档
- **Bonus Level**: 生成多种表示，适合检索场景
- 高精度设置会增加处理时间
- 大文件建议启用分块处理
- 多文件处理建议使用并行处理
- OCR处理对图像质量要求较高
