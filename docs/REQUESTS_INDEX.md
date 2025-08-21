# 请求类型与可选项索引

本目录给出常见请求模板与可选项，便于快速复制粘贴测试。

## 0. 文件上传（Upload）

### 0.1 纯文本上传（JSON） — POST `/api/v1/api/upload/text`

- 必填字段：
  - `content`：字符串，纯文本内容
- 可选字段：
  - `task_id`：字符串，任务ID（不传则自动创建）
  - `priority`：字符串，任务优先级（"1"=低, "2"=普通, "3"=高, "4"=紧急），默认"2"
  - `auto_detect`：布尔，是否自动检测文本格式，默认 `true`
  - `extension`：字符串，手动模式下的扩展名（如 `txt`/`md`/`html`）。当 `auto_detect=false` 时必须提供

自动检测示例（推荐）：
```json
{
  "content": "# 标题\n这是一个 Markdown 文档\n- 列表项1\n- 列表项2",
  "auto_detect": true
}
```

手动指定扩展名示例：
```json
{
  "content": "这是纯文本内容",
  "auto_detect": false,
  "extension": "txt"
}
```

带优先级示例：
```json
{
  "content": "<div>HTML内容</div>",
  "priority": "3",
  "auto_detect": false,
  "extension": "html"
}
```

返回体（示意）：
```json
{
    "task_id": "uuid",
    "total_files": 1,
    "successful_uploads": 1,
    "failed_uploads": 0,
    "files": [
        {
            "file_uuid": "uuid",
            "original_filename": "text_uuid.md",
            "file_path": "uploads/<task_id>/uuid.md",
            "file_size": 1234,
            "status": "success",
            "error_message": null
        }
    ],
    "message": "文本内容上传成功，文件名: text_uuid.md"
}
```

注意：该接口仅接收 `application/json` 请求体；若发送表单会触发 422 校验错误。

### 0.2 文件流上传（Multipart） — POST `/api/v1/api/upload/stream`

- 表单字段：
  - `files`：文件数组（一个或多个）
  - `task_id`（可选）
  - `priority`（可选，值 1-4，默认 2）

示例（curl）：
```
curl -X POST "http://localhost:5015/api/v1/api/upload/stream" \
  -F "files=@/path/to/a.pdf" \
  -F "files=@/path/to/b.md" \
  -F "priority=3"
```

### 0.3 路径上传（JSON） — POST `/api/v1/api/upload/file`

请求体（与 `FilePathRequest` 对齐）：
```json
{
  "file_paths": [
    "D:/docs/a.pdf",
    "D:/docs/b.docx"
  ],
  "task_id": "optional-task-id"
}
```

### 0.4 提交文件处理任务（JSON） — POST `/api/v1/file/process`

请求体使用 `FileProcessRequest` 模型。必填字段：
- `task_id`：任务ID
- `purpose`：处理目的，必须为 `"content_reading"` 或 `{"value": "content_reading"}`
- `target_format`：输出格式，支持 `"plain_text"`, `"markdown"`, `"dataframe"`

可选字段：
- `table_precision`：表格精度（0-20），默认10
- `enable_chunking`：是否分块，默认false
- `chunking_strategy`：分块策略，默认"auto"
- `chunk_size`：分块大小，默认1000
- `chunk_overlap`：重叠大小，默认200
- `chunking_config`：分块详细配置
- `enable_multi_file_summary`：是否多文件摘要，默认false
- `enable_extract`：是否信息抽取，默认false
- `extract_config`：抽取配置（当enable_extract=true时必须）
- `enable_ocr`：是否OCR，默认true
- `ocr_mode`：OCR模式，默认"prompt_ocr"

基础示例：
```json
{
  "task_id": "demo_001",
  "purpose": "content_reading",
  "target_format": "markdown"
}
```

详细示例请参考 `docs/api_usage_examples.md` 中的"文件处理API使用示例"。

### 0.5 健康检查

- GET `/api/v1/health`
- GET `/api/v1/ping`

### 0.6 任务管理

#### 获取任务详情 — GET `/api/v1/api/tasks/{task_id}`

返回指定任务的详细信息。

#### 获取任务列表 — GET `/api/v1/api/tasks`

查询参数：
- `status`（可选）：按状态过滤，值为 `pending`/`active`/`processing`/`completed`/`failed`/`cancelled`
- `limit`（可选）：返回数量限制，默认100，范围1-1000

#### 获取队列状态 — GET `/api/v1/api/tasks/queue/status`

返回当前队列统计信息，包含各状态任务数量。

#### 更新任务状态 — PUT `/api/v1/api/tasks/{task_id}/status`

查询参数：
- `status`（必须）：新状态值
- `error_message`（可选）：错误信息

#### 删除任务 — DELETE `/api/v1/api/tasks/{task_id}`

删除指定任务文件。

#### 获取统计信息 — GET `/api/v1/api/tasks/stats`

返回任务统计信息，包含状态分布、文件数量、总大小等。

#### 清理已完成任务 — POST `/api/v1/api/tasks/cleanup`

清理状态为 `completed`/`failed`/`cancelled` 的任务文件。

#### 搜索任务 — GET `/api/v1/api/tasks/search`

查询参数：
- `keyword`（可选）：搜索关键词
- `status`（可选）：状态过滤
- `limit`（可选）：返回数量限制，默认50，范围1-200

### 0.7 信息抽取 — 基于 LangExtract

在文件处理时可启用信息抽取功能：

```json
{
  "task_id": "extract_demo",
  "purpose": "content_reading", 
  "target_format": "plain_text",
  "enable_extract": true,
  "extract_config": {
    "prompt": "请从文本中抽取人物和事件信息",
    "extractions": [
      {
        "text": "张三在2024年获得了优秀员工奖",
        "extractions": [
          {
            "extraction_class": "人物",
            "extraction_text": "张三",
            "attributes": {"角色": "员工"}
          },
          {
            "extraction_class": "事件", 
            "extraction_text": "获得了优秀员工奖",
            "attributes": {"时间": "2024年", "类型": "获奖"}
          }
        ]
      }
    ]
  }
}
```

### 0.8 OCR配置

支持的OCR模式：
- `"prompt_layout_all_en"`：包含布局信息（英文）
- `"prompt_layout_only_en"`：仅布局信息（英文）
- `"prompt_ocr"`：仅文本识别（默认）
- `"prompt_grounding_ocr"`：定位OCR

OCR配置示例：
```json
{
  "task_id": "ocr_demo",
  "purpose": "content_reading",
  "target_format": "plain_text", 
  "enable_ocr": true,
  "ocr_mode": "prompt_layout_all_en"
}
```

## 1. 基础读取

### 1.1 纯文本

```json
{
  "task_id": "demo_plain_001",
  "purpose": "content_reading",
  "target_format": "plain_text",
  "table_precision": 10
}
```

### 1.2 Markdown

```json
{
  "task_id": "demo_md_001",
  "purpose": "content_reading",
  "target_format": "markdown"
}
```

### 1.3 DataFrame（表格）

```json
{
  "task_id": "demo_df_001",
  "purpose": "content_reading",
  "target_format": "dataframe",
  "table_precision": 12
}
```

## 2. 分块（Chunking）

通用尺寸：
```json
{
  "enable_chunking": true,
  "chunk_size": 800,
  "chunk_overlap": 120
}
```

### 2.1 Level 1：character_splitting

```json
{
  "task_id": "demo_ch_001",
  "purpose": "content_reading",
  "target_format": "plain_text",
  "enable_chunking": true,
  "chunking_strategy": "character_splitting",
  "chunk_size": 1000,
  "chunk_overlap": 100
}
```

### 2.2 Level 2：recursive_character_splitting

```json
{
  "task_id": "demo_ch_002",
  "purpose": "content_reading",
  "target_format": "plain_text",
  "enable_chunking": true,
  "chunking_strategy": "recursive_character_splitting",
  "chunk_size": 1200,
  "chunk_overlap": 150,
  "chunking_config": {
    "recursive_splitting_config": {
      "separators": ["\n\n", "\n", ". ", ", ", " "],
      "keep_separator": true
    }
  }
}
```

### 2.3 Level 3：document_specific_splitting（Markdown）

```json
{
  "task_id": "demo_ch_003",
  "purpose": "content_reading",
  "target_format": "plain_text",
  "enable_chunking": true,
  "chunking_strategy": "document_specific_splitting",
  "chunk_size": 1500,
  "chunk_overlap": 200,
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

### 2.4 Level 4：semantic_splitting

```json
{
  "task_id": "demo_ch_004",
  "purpose": "content_reading",
  "target_format": "plain_text",
  "enable_chunking": true,
  "chunking_strategy": "semantic_splitting",
  "chunk_size": 800,
  "chunk_overlap": 120,
  "chunking_config": {
    "semantic_splitting_config": {
      "similarity_threshold": 0.3,
      "buffer_size": 1
    }
  }
}
```

#### semantic_splitting_config 参数说明

- `similarity_threshold` (float, 默认: 0.25): 相邻句子组合的相似度阈值，低于该值将产生分割点
- `buffer_size` (int, 默认: 1): 句子组合窗口大小，每个句子会与前后 buffer_size 个句子组合后计算embedding，用于减少噪音
- `embedding_model` (string, 可选): 覆盖默认的embedding模型
- `min_chunk_size` / `max_chunk_size` (int, 可选): 最小/最大chunk大小限制

### 2.5 Level 5：agentic_splitting（实验性）

```json
{
  "task_id": "demo_ch_005",
  "purpose": "content_reading",
  "target_format": "plain_text",
  "enable_chunking": true,
  "chunking_strategy": "agentic_splitting",
  "chunk_size": 1000,
  "chunk_overlap": 100,
  "chunking_config": {
    "agentic_splitting_config": {
      "llm_model": "your-llm-name",
      "chunking_prompt": "请在语义边界上切分文本并输出JSON数组",
      "max_tokens_per_chunk": 1024,
      "enable_thinking": false,
      "temperature": 0.0
    }
  }
}
```

### 2.6 Level 6：alternative_representation_chunking（替代表示分块）

```json
{
  "task_id": "demo_ch_006a",
  "purpose": "content_reading",
  "target_format": "plain_text",
  "enable_chunking": true,
  "chunking_strategy": "alternative_representation_chunking",
  "chunk_size": 1000,
  "chunk_overlap": 100,
  "chunking_config": {
    "alternative_representation_config": {
      "representation_types": ["outline", "code_blocks", "tables"],
      "indexing_strategy": "hybrid",
      "retrieval_optimized": true,
      "include_outline": true,
      "include_code_blocks": true,
      "include_tables": true
    }
  }
}
```

### 2.7 Level 6：custom_delimiter_splitting

```json
{
  "task_id": "demo_ch_006",
  "purpose": "content_reading",
  "target_format": "plain_text",
  "enable_chunking": true,
  "chunking_strategy": "custom_delimiter_splitting",
  "chunk_size": 800,
  "chunk_overlap": 120,
  "chunking_config": {
    "custom_delimiter_config": {"delimiter": "——END——"}
  }
}
```

注意：`custom_delimiter_config` 包含以下参数：
- `delimiter`：分隔符字符串，用于文本切分

### 2.8 Level 6+：custom_delimiter_splitting_with_chunk_size_and_leave_table_alone

```json
{
  "task_id": "demo_ch_007",
  "purpose": "content_reading",
  "target_format": "markdown",
  "enable_chunking": true,
  "chunking_strategy": "custom_delimiter_splitting_with_chunk_size_and_leave_table_alone",
  "chunk_size": 1000,
  "chunk_overlap": 100,
  "chunking_config": {
    "custom_delimiter_config": {"delimiter": "\n\n"}
  }
}
```

## 3. 摘要（Summary）

```json
{
  "task_id": "demo_sum_001",
  "purpose": "content_reading",
  "target_format": "plain_text",
  "enable_multi_file_summary": true,
  "summary_length": 300,
  "summary_focus": ["main_points", "key_findings", "recommendations"],
  "summary_return_top_k": 5
}
```

说明：当正文为空时，摘要短路为空；有内容则返回 `summary` 与 `summary_dict`。

## 4. 分块策略说明

### Alternative Representation Chunking（替代表示分块）

这个策略专门用于创建文档的替代表示形式，便于检索和索引：

- **衍生表示类型**：支持抽取大纲(outline)、代码块(code_blocks)、表格(tables)等
- **索引策略**：支持dense/sparse/hybrid三种索引方式
- **检索优化**：为检索系统优化存储这些衍生表示
- **适用场景**：构建文档索引、支持多模态检索、创建文档概览

### Level 6+: custom_delimiter_splitting_with_chunk_size_and_leave_table_alone

这个策略是 `custom_delimiter_splitting` 的增强版本，具有以下特点：

- **表格保持完整**：自动识别 markdown 表格并保持其完整性，不会被切分
- **文本按分隔符切分**：其他文本按指定的分隔符进行切分
- **智能合并处理**：切分后的文本段落进行智能合并，确保每块尽可能接近 `chunk_size`
- **适用场景**：处理包含表格的 markdown 文档，希望保持表格结构的同时对文本进行分块

**表格识别规则**：
- 包含 `|` 字符的行
- 下一行是分隔符行（如 `|-----|-----|`）
- 后续包含 `|` 的数据行

**智能合并规则**：
- 按分隔符切分文本段落
- 将相邻段落合并，直到接近目标 `chunk_size`
- 如果合并后超过目标大小，则在新块中开始
- 如果当前块太小（小于目标大小的50%），继续合并下一个段落

**配置参数**：
- `delimiter`：分隔符字符串（如 `"\n\n"` 表示按段落切分）
- `chunk_size`：每个文本块的目标字符数
- `chunk_overlap`：相邻文本块的重叠字符数（在智能合并中主要用于计算）

---

更多细节参见：`api_usage_examples.md` 与 README。


