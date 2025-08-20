# 请求类型与可选项索引

本目录给出常见请求模板与可选项，便于快速复制粘贴测试。

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
      "similarity_threshold": 0.3
    }
  }
}
```

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

### 2.6 Level 6：custom_delimiter_splitting

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

### 2.7 Level 6+：custom_delimiter_splitting_with_chunk_size_and_leave_table_alone

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


