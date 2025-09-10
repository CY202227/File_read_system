# 文件处理API使用示例

## 概述

本文档展示了如何使用文件处理系统的JSON参数结构。所有参数都使用BaseModel形式，提供更好的类型安全和验证。

接口路径：

- 文件处理主入口: `POST /api/v1/file/process`
- 文件内容读取: `POST /api/v1/file/read`
- 文件切片: `POST /api/v1/file/chunk`
- 文件总结: `POST /api/v1/file/summarize`
- 信息抽取: `POST /api/v1/file/extract`

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

## 文件处理功能

### 文件处理流程拆分

系统现在提供了四个独立的接口，可以分步执行文件处理流程：

1. **文件内容读取** (`/file/read`): 读取文件内容，支持OCR和表格精度设置
2. **文件切片** (`/file/chunk`): 对文件内容进行切片，如果未先调用/file/read则会自动调用
3. **文件总结** (`/file/summarize`): 对文件内容进行总结，如果未先调用/file/read则会自动调用
4. **信息抽取** (`/file/extract`): 基于LangExtract从文件内容中抽取结构化信息，如果未先调用/file/read则会自动调用

这些接口可以单独使用，也可以按顺序组合使用，满足不同的处理需求。用户可以直接调用/file/chunk、/file/summarize或/file/extract，系统会自动处理文件读取步骤。

### 1. 文件内容读取接口

#### 端点

- `POST /api/v1/file/read`

#### 参数

- `task_id`: 任务ID（必需）
- `purpose`: 读取文件的目的（当前仅接收 `content_reading`）
- `target_format`: 目标输出格式（`plain_text | markdown | dataframe`）
- `enable_ocr`: 是否启用OCR文本识别（默认为true）
- `ocr_mode`: OCR模式（默认为 `prompt_ocr`）
- `table_precision`: 表格精度（0-20）

#### 使用示例

```bash
curl -X POST "http://localhost:5015/api/v1/file/read" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "markdown"},
    "table_precision": {"value": 10}
  }'
```

#### 响应格式

```json
{
  "task_id": "task_20241201_001",
  "status": "completed",
  "progress": 100.0,
  "result_data": {
    "text": "# 文档标题\n\n这是文档内容..."
  },
  "processing_time": 1.25,
  "file_info": {...},
  "error_message": null,
  "error_details": null
}
```

### 2. 文件切片接口

#### 端点

- `POST /api/v1/file/chunk`

#### 什么是文件切片？

文件切片就像把一本厚书分成很多小章节一样。为什么要这样做呢？

- **便于处理**：大文件一次性处理会很慢，分成小块处理更快
- **提高效率**：可以并行处理多个小块
- **便于搜索**：在特定的小块中查找信息比在整个文件中查找更快
- **节省内存**：不需要一次性加载整个文件到内存中

#### 参数详解

##### 必需参数

**`task_id`** (字符串，必需)

- **含义**：任务的唯一标识符，就像给每个任务起的名字
- **为什么需要**：系统需要知道你要处理哪个文件，这个ID就是"身份证"
- **示例值**：`"task_20241201_001"` 或 `"my_document_001"`
- **注意事项**：如果这个ID对应的文件还没有被读取过，系统会自动先读取文件

##### 可选参数

**`chunking_strategy`** (对象，可选，默认值：`{"value": "auto"}`)

- **含义**：选择用什么方法来切分文件
- **为什么需要**：不同的切分方法适合不同的场景，就像切蛋糕可以用刀切、用线切、用手掰一样
- **可选值**：
  - `{"value": "auto"}` - 自动选择（推荐新手使用）
  - `{"value": "character_splitting"}` - 按字符数切分（最简单）
  - `{"value": "recursive_character_splitting"}` - 按段落和句子切分（保持结构）
  - `{"value": "document_specific_splitting"}` - 按文档类型切分（适合PDF、Markdown等）
  - `{"value": "semantic_splitting"}` - 按语义切分（最智能但最慢）
  - `{"value": "agentic_splitting"}` - 用AI智能切分（实验性功能）
  - `{"value": "custom_delimiter_splitting"}` - 按自定义分隔符切分
  - `{"value": "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone"}` - 按分隔符切分但保持表格完整

**`chunk_size`** (整数，可选，默认值：1000)

- **含义**：每个切片包含多少个字符
- **为什么需要**：就像决定每页书要印多少字一样，太大处理慢，太小信息不完整
- **取值范围**：100 - 99,999,999 字符
- **推荐值**：
  - 1000-1500：适合一般文档
  - 2000-3000：适合长文档
  - 500-800：适合需要精确处理的场景
- **注意事项**：这个值决定了每个切片的大小，影响处理速度和结果质量

**`chunk_overlap`** (整数，可选，默认值：200)

- **含义**：相邻切片之间重叠的字符数
- **为什么需要**：就像书页之间要有一些重复内容，避免重要信息被切断
- **取值范围**：0 - 1000 字符
- **推荐值**：
  - 100-200：适合一般文档
  - 300-500：适合需要保持上下文的长文档
  - 0：适合不需要上下文的简单切分
- **注意事项**：重叠越大，信息越完整，但切片数量也越多

**`chunking_config`** (对象，可选，默认值：`null`)

- **含义**：针对特定切分策略的详细配置
- **为什么需要**：当选择高级切分策略时，需要更精细的控制
- **使用场景**：只有在选择特定策略且需要自定义配置时才需要

#### 使用示例

##### 示例1：最简单的切片（推荐新手使用）

```bash
curl -X POST "http://localhost:5015/api/v1/file/chunk" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001"
  }'
```

**说明**：这个例子只提供了必需的 `task_id`，其他参数都使用默认值：

- 自动选择切分策略
- 每个切片1000字符
- 切片间重叠200字符

##### 示例2：自定义切片大小

```bash
curl -X POST "http://localhost:5015/api/v1/file/chunk" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001",
    "chunk_size": 1500,
    "chunk_overlap": 200
  }'
```

**说明**：这个例子适合处理较长的文档：

- 每个切片1500字符（比默认的1000字符大）
- 保持200字符的重叠，确保信息完整性

##### 示例3：按段落切分（保持文档结构）

```bash
curl -X POST "http://localhost:5015/api/v1/file/chunk" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001",
    "chunking_strategy": {"value": "recursive_character_splitting"},
    "chunk_size": 1500,
    "chunk_overlap": 200
  }'
```

**说明**：这个例子适合需要保持文档结构的场景：

- 使用 `recursive_character_splitting`策略，会尽量在段落和句子边界处切分
- 避免在句子中间切断，保持语义完整性

##### 示例4：处理包含表格的文档

```bash
curl -X POST "http://localhost:5015/api/v1/file/chunk" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001",
    "chunking_strategy": {"value": "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone"},
    "chunk_size": 2000,
    "chunk_overlap": 300,
    "chunking_config": {
        "custom_delimiter_config": {
            "delimiter": "——END——"
        }
    }
  }'
```

**说明**：这个例子适合处理包含表格的文档：

- 使用特殊策略保持表格完整
- 按自定义分隔符"——END——"切分
- 表格不会被切断，保持结构完整

##### 示例5：语义切分（最智能但最慢）

```bash
curl -X POST "http://localhost:5015/api/v1/file/chunk" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001",
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
  }'
```

**说明**：这个例子使用最智能的切分方法：

- 基于语义相似度切分，确保每个切片在语义上完整
- 需要更多计算资源，处理时间较长
- 适合对语义完整性要求很高的场景

#### 响应格式

```json
{
  "task_id": "task_20241201_001",
  "status": "completed",
  "progress": 100.0,
  "chunks": ["这是第一个文本块...", "这是第二个文本块..."],
  "derivatives": [],
  "per_file": [{
    "file_path": "combined_text",
    "count": 2,
    "chunks": ["这是第一个文本块...", "这是第二个文本块..."]
  }],
  "processing_time": 0.45,
  "chunks_meta": {
    "merged_count": 2,
    "per_file": [{"file_path": "combined_text", "count": 2}]
  },
  "error_message": null,
  "error_details": null
}
```

**响应字段说明**：

- `status`: 处理状态（completed=完成，processing=处理中，failed=失败）
- `chunks`: 切分后的文本块数组
- `per_file`: 每个文件的切分结果
- `processing_time`: 处理耗时（秒）
- `chunks_meta`: 切分元数据信息

### 3. 文件总结接口

#### 端点

- `POST /api/v1/file/summarize`

#### 参数

- `task_id`: 任务ID（必需，如果未先调用/file/read则会自动调用）
- `summary_length`: 总结长度（默认500字符）
- `summary_focus`: 总结重点关注的方面（默认["main_points", "key_findings", "recommendations"]）
- `summary_return_top_k`: 返回前K条要点（可选）

#### 使用示例

```bash
curl -X POST "http://localhost:5015/api/v1/file/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001",
    "summary_length": 800,
    "summary_focus": ["main_points", "key_findings", "recommendations"],
    "summary_return_top_k": 5
  }'
```

#### 响应格式

```json
{
  "task_id": "task_20241201_001",
  "status": "completed",
  "progress": 100.0,
  "summary": "- 要点1\n- 要点2\n- 要点3\n- 要点4\n- 要点5",
  "summary_dict": {
    "p1": "要点1",
    "p2": "要点2",
    "p3": "要点3",
    "p4": "要点4",
    "p5": "要点5"
  },
  "processing_time": 2.35,
  "summary_meta": {
    "length": 150,
    "paragraphs": 5,
    "top_k": 5
  },
  "error_message": null,
  "error_details": null
}
```

### 处理流程示例

#### 完整处理流程（分步执行）

1. 首先上传文件（使用现有的文件上传接口）
2. 读取文件内容：

```bash
curl -X POST "http://localhost:5015/api/v1/file/read" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "markdown"}
  }'
```

3. 对文件内容进行切片：

```bash
curl -X POST "http://localhost:5015/api/v1/file/chunk" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001",
    "chunking_strategy": {"value": "semantic_splitting"},
    "chunk_size": 1500,
    "chunk_overlap": 200
  }'
```

4. 生成文件总结：

```bash
curl -X POST "http://localhost:5015/api/v1/file/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001",
    "summary_length": 800,
    "summary_focus": ["main_points", "key_findings"]
  }'
```

5. 执行信息抽取：

```bash
curl -X POST "http://localhost:5015/api/v1/file/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_001",
    "extract_config": {
      "prompt": "请从文本中提取人物与事件，必须返回原文精确片段。",
      "extractions": [
        {
          "text": "示例原文片段：胡文容是市政协党组书记、主席。",
          "extractions": [
            {"extraction_class": "人物", "extraction_text": "胡文容", "attributes": {"职务": "市政协党组书记、主席"}}
          ]
        }
      ]
    }
  }'
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

## 使用示例(process接口)

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
            "embedding_model": "text-embedding-ada-002",
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
            "llm_model": "Qwen3",
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

### 5. 多文件总结

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

### 5.1 Summary 响应控制（Top-K）

```json
{
    "task_id": "task_20241201_004_stream",
    "purpose": {"value": "content_reading"},
    "target_format": {"value": "plain_text"},
    "summary_return_top_k": 5,
    "enable_multi_file_summary": true
}
```

### 4. 信息抽取接口

#### 端点

- `POST /api/v1/file/extract`

#### 什么是信息抽取？

信息抽取是从非结构化文本中提取结构化信息的过程，就像从一篇文章中自动找出所有人名、地点、事件等信息。这个功能基于LangExtract库实现，可以帮助你：

- **提取实体**：从文本中找出人名、组织、地点等实体
- **识别关系**：理解实体之间的关系（如"谁是谁的老板"）
- **抽取属性**：提取实体的属性信息（如"职务"、"年龄"等）
- **结构化数据**：将非结构化文本转换为可查询的结构化数据

#### 参数详解

##### 必需参数

**`task_id`** (字符串，必需)

- **含义**：任务的唯一标识符，就像给每个任务起的名字
- **为什么需要**：系统需要知道你要处理哪个文件，这个ID就是"身份证"
- **示例值**：`"task_20241201_001"` 或 `"my_document_001"`
- **注意事项**：如果这个ID对应的文件还没有被读取过，系统会自动先读取文件

**`extract_config`** (对象，必需)

- **含义**：信息抽取的配置参数，包括抽取提示词和示例
- **为什么需要**：系统需要知道你想抽取什么类型的信息，以及如何抽取
- **组成部分**：
  - `prompt`：抽取任务的指令，告诉系统要抽取什么
  - `extractions`：few-shot示例集合，帮助系统理解抽取任务

##### 可选参数

**`purpose`** (对象，可选，默认值：`{"value": "content_reading"}`)

- **含义**：读取文件的目的
- **为什么需要**：主要用于日志记录和分析

**`target_format`** (对象，可选，默认值：`{"value": "plain_text"}`)

- **含义**：目标输出格式
- **为什么需要**：指定文件内容的处理格式

**`enable_ocr`** (布尔值，可选，默认值：`true`)

- **含义**：是否启用OCR文本识别
- **为什么需要**：处理图像文件或PDF时需要

**`ocr_mode`** (对象，可选，默认值：`{"value": "prompt_ocr"}`)

- **含义**：OCR模式
- **为什么需要**：控制OCR的处理方式

#### 使用示例

##### 示例1：基础信息抽取

```bash
curl -X POST "http://localhost:5015/api/v1/file/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_005",
    "extract_config": {
      "prompt": "请从文本中提取人物与事件，必须返回原文精确片段。",
      "extractions": [
        {
          "text": "示例原文片段：胡文容是市政协党组书记、主席。",
          "extractions": [
            {"extraction_class": "人物", "extraction_text": "胡文容", "attributes": {"职务": "市政协党组书记、主席"}}
          ]
        }
      ]
    }
  }'
```

**说明**：这个例子演示了如何从文本中抽取人物信息：

- 提供了一个简单的抽取提示词，要求抽取人物与事件
- 提供了一个示例，告诉系统如何抽取人物及其属性

##### 示例2：多类型信息抽取

```bash
curl -X POST "http://localhost:5015/api/v1/file/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task_20241201_006",
    "extract_config": {
      "prompt": "请从文本中提取人物、组织机构和地点信息，必须返回原文精确片段。",
      "extractions": [
        {
          "text": "示例原文片段：李明在北京大学发表了演讲，中国科学院院长王伟也出席了活动。",
          "extractions": [
            {"extraction_class": "人物", "extraction_text": "李明", "attributes": {}},
            {"extraction_class": "人物", "extraction_text": "王伟", "attributes": {"职务": "中国科学院院长"}},
            {"extraction_class": "组织", "extraction_text": "北京大学", "attributes": {}},
            {"extraction_class": "组织", "extraction_text": "中国科学院", "attributes": {}}
          ]
        }
      ]
    }
  }'
```

**说明**：这个例子演示了如何同时抽取多种类型的信息：

- 提示词要求抽取人物、组织机构和地点信息
- 示例中展示了如何抽取多个实体及其属性

#### 响应格式

```json
{
  "task_id": "task_20241201_005",
  "status": "completed",
  "progress": 100.0,
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
    },
    {
      "extraction_class": "事件",
      "extraction_text": "会议",
      "char_interval": {"start_pos": 45, "end_pos": 47},
      "alignment_status": "match_exact",
      "extraction_index": 2,
      "group_index": 0,
      "description": null,
      "attributes": {"时间": "2024年5月10日"}
    }
  ],
  "processing_time": 1.75,
  "error_message": null,
  "error_details": null
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

**策略名称**：`character_splitting`
**工作原理**：就像用尺子量长度一样，不管内容是什么，每隔固定字符数就切一刀
**优点**：

- 速度最快，就像用剪刀剪纸条一样简单
- 资源消耗最少，适合处理大量文档
- 结果可预测，每个切片大小完全一致
  **缺点**：
- 可能会在句子中间切断，破坏语义完整性
- 不考虑文档结构，段落、表格等可能被破坏
  **适用场景**：
- 需要快速处理大量文档
- 对语义完整性要求不高
- 文档结构简单，主要是连续文本
  **示例**：如果设置 `chunk_size: 1000`，那么第1000个字符处就会被切断，不管那里是句号、逗号还是字母中间

**参数配置**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "character_splitting"},
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

**参数说明**：

- `chunk_size`：每个切片的字符数，范围100-99,999,999，默认1000
- `chunk_overlap`：相邻切片的重叠字符数，范围0-1000，默认200
- **注意**：此策略不需要 `chunking_config`，所有配置都通过基础参数控制

#### Level 2: Recursive Character Text Splitting (递归字符分块)

**策略名称**：`recursive_character_splitting`
**工作原理**：先尝试在段落边界切分，如果还是太大，就在句子边界切分，最后才在字符边界切分
**优点**：

- 尽量保持段落和句子的完整性
- 比Level 1更智能，但速度仍然很快
- 可以自定义分隔符优先级
  **缺点**：
- 仍然可能在单词中间切断
- 需要预先定义分隔符列表
  **适用场景**：
- 需要保持文档基本结构
- 文档有明显的段落和句子分隔
- 对处理速度有一定要求

**参数配置**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "recursive_character_splitting"},
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "chunking_config": {
    "recursive_splitting_config": {
      "separators": ["\n\n", "\n", ". ", "! ", "? ", " ", ""],
      "keep_separator": true
    }
  }
}
```

**详细参数说明**：

**基础参数**：

- `chunk_size`：目标切片大小，范围100-99,999,999，默认1000
- `chunk_overlap`：重叠字符数，范围0-1000，默认200

**`recursive_splitting_config` 配置**：

- `separators`（必需）：分隔符列表，按优先级排序
  - `"\n\n"`：双换行，表示段落分隔
  - `"\n"`：单换行，表示行分隔
  - `". "`：句号+空格，表示句子结束
  - `"! "`：感叹号+空格，表示句子结束
  - `"? "`：问号+空格，表示句子结束
  - `" "`：空格，表示单词分隔
  - `""`：空字符串，表示字符分隔（最后选择）
- `keep_separator`（可选）：是否保留分隔符在切片中
  - `true`：保留分隔符（推荐，保持文本完整性）
  - `false`：不保留分隔符（可能破坏文本结构）

**配置示例**：

**保持段落完整**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "recursive_character_splitting"},
  "chunk_size": 1500,
  "chunk_overlap": 300,
  "chunking_config": {
    "recursive_splitting_config": {
      "separators": ["\n\n", "\n", ". ", "! ", "? "],
      "keep_separator": true
    }
  }
}
```

**优先按句子切分**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "recursive_character_splitting"},
  "chunk_size": 800,
  "chunk_overlap": 150,
  "chunking_config": {
    "recursive_splitting_config": {
      "separators": [". ", "! ", "? ", "\n", " "],
      "keep_separator": true
    }
  }
}
```

#### Level 3: Document Specific Splitting (文档特定分块)

**策略名称**：`document_specific_splitting`
**工作原理**：针对不同文档类型使用专门的切分规则，比如PDF按页面切分，Markdown按标题切分，代码按函数切分
**优点**：

- 最了解特定文档类型的结构
- 能保持文档的原始格式和结构
- 切分结果最符合文档的原始组织方式
  **缺点**：
- 只支持特定的文档类型
- 配置相对复杂
- 处理速度中等
  **适用场景**：
- 处理特定格式的文档（PDF、Markdown、HTML、Python代码等）
- 需要保持文档的原始结构
- 对文档类型有明确要求

**参数配置**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "document_specific_splitting"},
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "chunking_config": {
    "document_specific_config": {
      "document_type": "markdown",
      "preserve_headers": true,
      "preserve_code_blocks": true,
      "preserve_lists": true,
      "preserve_tables": true,
      "preserve_links": true,
      "preserve_images": true
    }
  }
}
```

**详细参数说明**：

**基础参数**：

- `chunk_size`：目标切片大小，范围100-99,999,999，默认1000
- `chunk_overlap`：重叠字符数，范围0-1000，默认200

**`document_specific_config` 配置**：

- `document_type`（必需）：文档类型

  - `"markdown"`：Markdown文档
  - `"html"`：HTML文档
  - `"pdf"`：PDF文档
  - `"python"`：Python代码文件
  - `"javascript"`：JavaScript代码文件
  - `"java"`：Java代码文件
  - `"cpp"`：C++代码文件
  - `"csharp"`：C#代码文件
  - `"go"`：Go代码文件
  - `"rust"`：Rust代码文件
- `preserve_headers`（可选）：是否保持标题结构

  - `true`：保持标题完整，不在标题中间切分
  - `false`：允许在标题中间切分
  - 默认值：`true`
- `preserve_code_blocks`（可选）：是否保持代码块完整

  - `true`：保持代码块完整，不在代码中间切分
  - `false`：允许在代码中间切分
  - 默认值：`true`
- `preserve_lists`（可选）：是否保持列表完整

  - `true`：保持列表项完整，不在列表项中间切分
  - `false`：允许在列表项中间切分
  - 默认值：`true`
- `preserve_tables`（可选）：是否保持表格完整

  - `true`：保持表格完整，不在表格中间切分
  - `false`：允许在表格中间切分
  - 默认值：`true`
- `preserve_links`（可选）：是否保持链接完整

  - `true`：保持链接完整，不在链接中间切分
  - `false`：允许在链接中间切分
  - 默认值：`true`
- `preserve_images`（可选）：是否保持图片引用完整

  - `true`：保持图片引用完整，不在图片引用中间切分
  - `false`：允许在图片引用中间切分
  - 默认值：`true`

**配置示例**：

**Markdown文档处理**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "document_specific_splitting"},
  "chunk_size": 1200,
  "chunk_overlap": 250,
  "chunking_config": {
    "document_specific_config": {
      "document_type": "markdown",
      "preserve_headers": true,
      "preserve_code_blocks": true,
      "preserve_lists": true,
      "preserve_tables": true
    }
  }
}
```

**Python代码处理**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "document_specific_splitting"},
  "chunk_size": 800,
  "chunk_overlap": 150,
  "chunking_config": {
    "document_specific_config": {
      "document_type": "python",
      "preserve_code_blocks": true
    }
  }
}
```

#### Level 4: Semantic Splitting (语义分块)

**策略名称**：`semantic_splitting`
**工作原理**：使用AI模型计算文本的语义相似度，将语义相近的句子组合在一起，语义差异大的地方进行切分
**优点**：

- 最智能的切分方法，能理解文本含义
- 每个切片在语义上都是完整的
- 适合后续的AI分析和处理
  **缺点**：
- 处理速度最慢，需要计算语义嵌入
- 资源消耗最大，需要AI模型
- 结果可能不够稳定，依赖模型质量
  **适用场景**：
- 需要最高质量的语义完整性
- 后续要进行AI分析或问答
- 对处理速度要求不高

**参数配置**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "semantic_splitting"},
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "chunking_config": {
    "semantic_splitting_config": {
      "embedding_model": "text-embedding-ada-002",
      "similarity_threshold": 0.8,
      "buffer_size": 1,
      "min_chunk_size": 100,
      "max_chunk_size": 2000,
      "chunk_overlap": 200
    }
  }
}
```

**详细参数说明**：

**基础参数**：

- `chunk_size`：目标切片大小，范围100-99,999,999，默认1000
- `chunk_overlap`：重叠字符数，范围0-1000，默认200

**`semantic_splitting_config` 配置**：

- `embedding_model`（必需）：使用的AI模型名称

  - 默认值：`"text-embedding-ada-002"`（系统默认模型）
  - 可以覆盖为其他支持的模型名称
  - 注意：此参数会覆盖系统默认的向量模型配置
- `similarity_threshold`（必需）：语义相似度阈值

  - 范围：0.0 - 1.0
  - `0.0`：完全不相似
  - `1.0`：完全相同
  - 推荐值：`0.7 - 0.9`
  - 值越高，切片越精确，但数量可能越多
  - 值越低，切片越宽松，但可能破坏语义完整性
- `buffer_size`（可选）：句子组合窗口大小

  - 范围：1 - 10
  - 默认值：`1`
  - 作用：减少噪音并增强语义连贯性
  - 值越大，考虑更多上下文，但处理更慢
- `min_chunk_size`（可选）：最小切片大小

  - 范围：50 - 1000
  - 默认值：`100`
  - 作用：避免产生过小的切片
  - 如果切片小于此值，会尝试与相邻切片合并
- `max_chunk_size`（可选）：最大切片大小

  - 范围：500 - 5000
  - 默认值：`2000`
  - 作用：限制切片的最大大小
  - 如果切片超过此值，会强制切分
- `chunk_overlap`（可选）：语义切片的重叠大小

  - 范围：0 - 500
  - 默认值：`200`
  - 作用：确保相邻切片之间有足够的上下文
  - 注意：此参数会覆盖基础参数中的 `chunk_overlap`

**配置示例**：

**高质量语义切分**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "semantic_splitting"},
  "chunk_size": 1200,
  "chunk_overlap": 250,
  "chunking_config": {
    "semantic_splitting_config": {
      "embedding_model": "text-embedding-ada-002",
      "similarity_threshold": 0.9,
      "buffer_size": 2,
      "min_chunk_size": 200,
      "max_chunk_size": 2500,
      "chunk_overlap": 300
    }
  }
}
```

**快速语义切分**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "semantic_splitting"},
  "chunk_size": 800,
  "chunk_overlap": 150,
  "chunking_config": {
    "semantic_splitting_config": {
      "embedding_model": "text-embedding-ada-002",
      "similarity_threshold": 0.7,
      "buffer_size": 1,
      "min_chunk_size": 100,
      "max_chunk_size": 1500,
      "chunk_overlap": 200
    }
  }
}
```

#### Level 5: Agentic Splitting (智能代理分块)

**策略名称**：`agentic_splitting`
**工作原理**：使用大语言模型（如GPT）来理解文档内容，然后智能决定在哪里切分
**优点**：

- 最灵活，可以理解复杂的文档结构
- 能处理各种特殊情况和边缘情况
- 切分结果最符合人类理解
  **缺点**：
- 成本最高，每次切分都需要调用AI模型
- 处理速度最慢
- 结果可能不够稳定，依赖AI模型的判断
  **适用场景**：
- 处理非常复杂的文档结构
- 对切分质量要求极高
- 成本不是主要考虑因素

**参数配置**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "agentic_splitting"},
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "chunking_config": {
    "agentic_splitting_config": {
      "llm_model": "Qwen3",
      "chunking_prompt": "请将以下文本按照语义完整性进行分块，确保每个分块都是一个完整的语义单元。",
      "max_tokens_per_chunk": 2000,
      "preserve_context": true,
      "temperature": 0.1,
      "max_retries": 3
    }
  }
}
```

**详细参数说明**：

**基础参数**：

- `chunk_size`：目标切片大小，范围100-99,999,999，默认1000
- `chunk_overlap`：重叠字符数，范围0-1000，默认200

**`agentic_splitting_config` 配置**：

- `llm_model`（必需）：使用的大语言模型名称

  - 默认值：`"Qwen3"`（系统默认模型）
  - 可以覆盖为其他支持的模型名称
  - 注意：此参数会覆盖系统默认的LLM模型配置
- `chunking_prompt`（必需）：给AI的切分指令

  - 描述：详细说明如何切分文档
  - 长度：建议50-200字符
  - 示例：
    - "请将以下文本按照语义完整性进行分块，确保每个分块都是一个完整的语义单元。"
    - "请将文档按照主题和逻辑结构进行切分，保持每个切片的语义完整性。"
    - "请按照段落和章节的自然边界来切分文档，避免在句子中间切断。"
- `max_tokens_per_chunk`（必需）：每个切片的最大token数

  - 范围：500 - 4000
  - 默认值：`2000`
  - 作用：限制每个切片的大小，避免超出模型的处理能力
  - 注意：此值应该小于模型的上下文窗口大小
- `preserve_context`（可选）：是否保持上下文信息

  - `true`：在切分时考虑前后文的连贯性
  - `false`：只考虑当前文本片段
  - 默认值：`true`
- `temperature`（可选）：AI模型的创造性程度

  - 范围：0.0 - 1.0
  - `0.0`：最确定性，结果最一致
  - `1.0`：最随机，结果最多样
  - 推荐值：`0.1 - 0.3`（切分任务需要确定性）
  - 默认值：`0.1`
- `max_retries`（可选）：最大重试次数

  - 范围：1 - 5
  - 默认值：`3`
  - 作用：当AI模型返回错误结果时，自动重试
  - 注意：重试会增加成本和处理时间

**配置示例**：

**高质量智能切分**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "agentic_splitting"},
  "chunk_size": 1500,
  "chunk_overlap": 300,
        "chunking_config": {
        "agentic_splitting_config": {
          "llm_model": "Qwen3",
          "chunking_prompt": "请将以下文本按照语义完整性和逻辑结构进行分块，确保每个分块都是一个完整的主题单元，保持段落和章节的完整性。",
          "max_tokens_per_chunk": 3000,
          "preserve_context": true,
          "temperature": 0.1,
          "max_retries": 3
        }
      }
}
```

**成本优化智能切分**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "agentic_splitting"},
  "chunk_size": 800,
  "chunk_overlap": 150,
  "chunking_config": {
    "agentic_splitting_config": {
      "llm_model": "Qwen3",
      "chunking_prompt": "请将文本按照段落和句子的自然边界进行切分，保持语义完整性。",
      "max_tokens_per_chunk": 1500,
      "preserve_context": false,
      "temperature": 0.1,
      "max_retries": 2
    }
  }
}
```

**学术文档智能切分**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "agentic_splitting"},
  "chunk_size": 2000,
  "chunk_overlap": 400,
  "chunking_config": {
    "agentic_splitting_config": {
      "llm_model": "Qwen3",
      "chunking_prompt": "请按照学术论文的结构进行切分，保持每个切片的逻辑完整性和论证的连贯性，优先在章节、段落和子段落的边界处切分。",
      "max_tokens_per_chunk": 3500,
      "preserve_context": true,
      "temperature": 0.1,
      "max_retries": 3
    }
  }
}
```

#### Level 6: Custom Delimiter Splitting (自定义分隔符分块)

**策略名称**：`custom_delimiter_splitting`
**工作原理**：使用用户自定义的分隔符来切分文档，比如用"——END——"、"===分割线==="等
**优点**：

- 完全可控，切分位置由用户决定
- 适合有特定格式要求的文档
- 处理速度快，结果可预测
  **缺点**：
- 需要文档中预先包含分隔符
- 不够灵活，只能按固定模式切分
  **适用场景**：
- 文档有固定的分隔符标记
- 需要按特定规则切分
- 对切分位置有精确要求

**参数配置**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "custom_delimiter_splitting"},
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "chunking_config": {
    "custom_delimiter_config": {
      "delimiter": "——END——"
    }
  }
}
```

**详细参数说明**：

**基础参数**：

- `chunk_size`：目标切片大小，范围100-99,999,999，默认1000
- `chunk_overlap`：重叠字符数，范围0-1000，默认200

**`custom_delimiter_config` 配置**：

- `delimiter`（必需）：自定义分隔符

  - 类型：字符串
  - 长度：建议1-50字符
  - 示例：
    - `"——END——"`：中文分隔符
    - `"===分割线==="`：中文分割线
    - `"---END---"`：英文分隔符
    - `"###"`：Markdown标题分隔符
    - `"<hr>"`：HTML分隔线
    - `"---"`：YAML分隔符

**配置示例**：

**中文文档分隔符**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "custom_delimiter_splitting"},
  "chunk_size": 1200,
  "chunk_overlap": 200,
  "chunking_config": {
    "custom_delimiter_config": {
      "delimiter": "——END——",
      "include_delimiter": true,
      "trim_whitespace": true,
      "case_sensitive": false
    }
  }
}
```

**Markdown文档分隔符**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "custom_delimiter_splitting"},
  "chunk_size": 1000,
  "chunk_overlap": 150,
  "chunking_config": {
    "custom_delimiter_config": {
      "delimiter": "###"
    }
  }
}
```

**HTML文档分隔符**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "custom_delimiter_splitting"},
  "chunk_size": 1500,
  "chunk_overlap": 250,
  "chunking_config": {
    "custom_delimiter_config": {
      "delimiter": "<hr>"
    }
  }
}
```

#### Level 6+: Custom Delimiter with Table Preservation (保持表格完整的自定义分隔符切分)

**策略名称**：`custom_delimiter_splitting_with_chunk_size_and_leave_table_alone`
**工作原理**：按自定义分隔符切分，但会自动识别并保持Markdown表格的完整性
**优点**：

- 既能按分隔符切分，又能保持表格完整
- 特别适合包含表格的文档
- 智能合并相邻段落，确保切片大小接近目标值
  **缺点**：
- 配置相对复杂
- 只支持Markdown格式的表格
  **适用场景**：
- 文档包含表格内容
- 需要按分隔符切分但保持表格完整
- 对切片大小有要求

**参数配置**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone"},
  "chunk_size": 2000,
  "chunk_overlap": 300,
  "chunking_config": {
    "custom_delimiter_config": {
      "delimiter": "——END——"
    }
  }
}
```

**详细参数说明**：

**基础参数**：

- `chunk_size`：目标切片大小，范围100-99,999,999，默认2000
- `chunk_overlap`：重叠字符数，范围0-1000，默认300

**`custom_delimiter_config` 配置**：

- 与Level 6相同，包含所有分隔符相关配置

**智能合并机制**：

- 将相邻段落合并，直到接近目标切片大小
- 确保每个切片尽可能接近 `chunk_size`设置的值

**配置示例**：

**数据报告处理**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone"},
  "chunk_size": 2500,
  "chunk_overlap": 400,
  "chunking_config": {
    "custom_delimiter_config": {
      "delimiter": "=== 章节结束 ==="
    }
  }
}
```

**财务报告处理**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone"},
  "chunk_size": 3000,
  "chunk_overlap": 500,
  "chunking_config": {
    "custom_delimiter_config": {
      "delimiter": "——财务数据结束——"
    }
  }
}
```

#### Bonus Level: Alternative Representation Chunking (替代表示分块)

**策略名称**：`alternative_representation_chunking`
**工作原理**：不仅切分文本，还生成多种表示形式，如摘要、关键词、实体识别、情感分析等
**优点**：

- 提供多种文本表示方式
- 特别适合检索和索引场景
- 可以同时获得文本切片和结构化信息
  **缺点**：
- 处理复杂度高
- 需要额外的AI模型支持
- 配置复杂
  **适用场景**：
- 构建文档检索系统
- 需要多种文本表示方式
- 对检索效果有高要求

**参数配置**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "alternative_representation_chunking"},
  "chunk_size": 1000,
  "chunk_overlap": 0,
  "chunking_config": {
    "alternative_representation_config": {
      "include_outline": true,
      "include_code_blocks": true,
      "include_tables": true
    }
  }
}
```

**详细参数说明**：

**基础参数**：

- `chunk_size`：目标切片大小，范围100-99,999,999，默认1000
- `chunk_overlap`：重叠字符数，范围0-1000，默认200

**`alternative_representation_config` 配置**：

- `representation_types`（必需）：表示类型列表

  - `"summary"`：生成文本摘要
  - `"keywords"`：提取关键词
  - `"entities"`：实体识别
  - `"sentiment"`：情感分析
  - `"topics"`：主题识别
  - `"language"`：语言检测
  - 可以组合多个类型
- `indexing_strategy`（必需）：索引策略

  - `"hybrid"`：混合策略，结合多种索引方法
  - `"vector"`：向量索引，基于语义相似度
  - `"keyword"`：关键词索引，基于精确匹配
  - `"semantic"`：语义索引，基于AI理解
  - 默认值：`"hybrid"`
- `retrieval_optimized`（必需）：是否优化检索效果

  - `true`：优化检索效果，生成更适合检索的表示
  - `false`：标准表示，平衡检索效果和处理速度
  - 默认值：`true`
- `embedding_model`（可选）：使用的AI模型名称

  - 默认值：`"text-embedding-ada-002"`（系统默认模型）
  - 可以覆盖为其他支持的模型名称
- `summary_length`（可选）：摘要长度

  - 范围：50 - 500字符
  - 默认值：`200`
  - 作用：控制生成的摘要长度
- `max_keywords`（可选）：最大关键词数量

  - 范围：5 - 50
  - 默认值：`10`
  - 作用：限制提取的关键词数量
- `entity_types`（可选）：识别的实体类型

  - 选项：
    - `"PERSON"`：人名
    - `"ORG"`：组织机构
    - `"LOC"`：地点
    - `"DATE"`：日期
    - `"MONEY"`：金额
    - `"PERCENT"`：百分比
    - `"TIME"`：时间
  - 默认值：`["PERSON", "ORG", "LOC", "DATE"]`
- `sentiment_analysis`（可选）：是否进行情感分析

  - `true`：分析文本情感（正面、负面、中性）
  - `false`：不进行情感分析
  - 默认值：`true`
- `language_detection`（可选）：是否进行语言检测

  - `true`：检测文本语言
  - `false`：不进行语言检测
  - 默认值：`true`

**配置示例**：

**检索优化配置**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "alternative_representation_chunking"},
  "chunk_size": 1200,
  "chunk_overlap": 250,
  "chunking_config": {
    "alternative_representation_config": {
      "representation_types": ["summary", "keywords", "entities", "sentiment"],
      "indexing_strategy": "hybrid",
      "retrieval_optimized": true,
      "embedding_model": "text-embedding-ada-002",
      "summary_length": 300,
      "max_keywords": 15,
      "entity_types": ["PERSON", "ORG", "LOC", "DATE", "MONEY"],
      "sentiment_analysis": true,
      "language_detection": true
    }
  }
}
```

**快速索引配置**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "alternative_representation_chunking"},
  "chunk_size": 800,
  "chunk_overlap": 150,
  "chunking_config": {
    "alternative_representation_config": {
      "representation_types": ["keywords", "entities"],
      "indexing_strategy": "keyword",
      "retrieval_optimized": false,
      "max_keywords": 8,
      "entity_types": ["PERSON", "ORG", "LOC"],
      "sentiment_analysis": false,
      "language_detection": false
    }
  }
}
```

**多语言文档处理**：

```json
{
  "task_id": "58b19e5f-90f2-448c-8fdc-9c2a73f4f95e",
  "chunking_strategy": {"value": "alternative_representation_chunking"},
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "chunking_config": {
    "alternative_representation_config": {
      "representation_types": ["summary", "keywords", "entities", "language"],
      "indexing_strategy": "semantic",
      "retrieval_optimized": true,
      "embedding_model": "text-embedding-ada-002",
      "summary_length": 250,
      "max_keywords": 12,
      "entity_types": ["PERSON", "ORG", "LOC", "DATE"],
      "sentiment_analysis": true,
      "language_detection": true
    }
  }
}
```

### Summary 响应控制

- `summary_return_top_k` (int): 返回前 K 条要点；当无内容时短路为空

### 兼容纯字符串输入

- 可将 `purpose`、`target_format`、`content_return_format`、`cleaning_level`、`chunking_strategy` 直接传为字符串
- 服务端会自动包裹为 `{ "value": "..." }` 后再校验

## 最佳实践

1. **任务ID**: 使用有意义的ID，便于跟踪和调试
2. **精度设置**: 根据文件大小和性能要求选择合适的表格精度
3. **分块大小**: 根据后续处理需求设置合适的分块大小
4. **自定义参数**: 充分利用custom_parameters字段进行扩展
5. **错误处理**: 始终检查响应状态和错误信息
6. **分步处理**: 对于复杂任务，考虑使用分步接口（/file/read → /file/chunk → /file/summarize）

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

### 🚀 处理速度对比

**最快（Level 1-2）：**

- `character_splitting`: 就像用剪刀剪纸条，速度最快
- `recursive_character_splitting`: 稍微慢一点，但仍然是快速处理
- **适用场景**：批量处理、实时处理、资源受限环境

**中等（Level 3）：**

- `document_specific_splitting`: 需要分析文档结构，速度中等
- **适用场景**：特定格式文档、需要保持结构的场景

**较慢（Level 4）：**

- `semantic_splitting`: 需要计算语义嵌入，速度较慢
- **适用场景**：高质量要求、后续AI分析

**最慢（Level 5）：**

- `agentic_splitting`: 需要调用大语言模型，速度最慢
- **适用场景**：实验性使用、极高质量要求

### 💾 资源消耗对比

**内存占用：**

- **低消耗**：Level 1-2，适合内存受限环境
- **中等消耗**：Level 3，需要加载文档结构信息
- **高消耗**：Level 4-5，需要加载AI模型

**CPU使用：**

- **低使用**：Level 1-2，简单的字符串操作
- **中等使用**：Level 3，文档解析和结构分析
- **高使用**：Level 4-5，AI模型推理

**网络请求：**

- **无网络**：Level 1-3，本地处理
- **需要网络**：Level 4-5，可能需要下载模型或调用API

### 📈 性能优化建议

#### 1. 批量处理优化

```json
{
  "chunking_strategy": {"value": "character_splitting"},
  "chunk_size": 800,
  "chunk_overlap": 100
}
```

**为什么这样优化？**

- 选择最快的策略
- 减少切片大小，加快处理
- 减少重叠，减少重复计算

#### 2. 质量优先优化

```json
{
  "chunking_strategy": {"value": "semantic_splitting"},
  "chunk_size": 1500,
  "chunk_overlap": 300,
  "chunking_config": {
    "semantic_splitting_config": {
      "similarity_threshold": 0.9,
      "min_chunk_size": 1000,
      "max_chunk_size": 2000
    }
  }
}
```

**为什么这样优化？**

- 选择最智能的策略
- 增加切片大小，减少切片数量
- 提高相似度阈值，确保质量

#### 3. 平衡优化

```json
{
  "chunking_strategy": {"value": "recursive_character_splitting"},
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

**为什么这样优化？**

- 选择平衡的策略
- 适中的切片大小
- 适中的重叠大小

### 🎯 实际性能数据参考

**注意**：以下数据仅供参考，实际性能取决于文档内容、系统配置等因素

| 文档大小 | 策略                              | 预期时间 | 内存使用 | 切片数量  |
| -------- | --------------------------------- | -------- | -------- | --------- |
| 1MB      | `character_splitting`           | 1-2秒    | 低       | 约1000个  |
| 1MB      | `recursive_character_splitting` | 2-3秒    | 低       | 约1000个  |
| 1MB      | `semantic_splitting`            | 10-20秒  | 高       | 约800个   |
| 10MB     | `character_splitting`           | 5-10秒   | 中       | 约10000个 |
| 10MB     | `semantic_splitting`            | 2-5分钟  | 高       | 约8000个  |

### 💡 性能优化小贴士

1. **从小开始**：先用简单策略测试，再逐步优化
2. **监控资源**：注意内存和CPU使用情况
3. **批量处理**：一次处理多个文档比逐个处理效率高
4. **缓存结果**：相同文档的切片结果可以缓存
5. **异步处理**：对于大文档，考虑异步处理
6. **参数调优**：根据实际效果调整参数，不要盲目追求完美
