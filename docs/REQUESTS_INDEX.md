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

---

更多细节参见：`api_usage_examples.md` 与 README。


