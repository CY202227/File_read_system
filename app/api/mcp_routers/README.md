# 文件阅读系统 MCP 服务器

File Reading System MCP Server

这是一个基于 [FastMCP](https://gofastmcp.com) 实现的 Model Context Protocol (MCP) 服务器，提供文件上传和处理相关的工具。

## 功能特性

### 文件上传工具
- `upload_files_by_stream`: 通过文件路径上传文件（支持单个或多个文件）
- `upload_text_content_tool`: 上传纯文本内容

### 文件处理工具
- `process_file_tool`: 提交文件处理任务（读取、转换等）
- `read_file_content_tool`: 文件内容读取接口
- `chunk_file_content_tool`: 文件切片接口
- `summarize_file_content_tool`: 文件总结接口
- `extract_file_content_tool`: 信息抽取接口（基于 LangExtract）

## 快速开始

### 1. 安装依赖

确保已安装所有必要的依赖：

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

#### 使用 Python 脚本启动

```bash
# 启动 stdio 模式的 MCP 服务器（默认）
python app/api/mcp_routers/run_mcp_server.py

# 启动 HTTP 模式的 MCP 服务器
python app/api/mcp_routers/run_mcp_server.py --transport http --port 8000

# 启动 SSE 模式的 MCP 服务器
python app/api/mcp_routers/run_mcp_server.py --transport sse --port 8001
```

#### 使用 FastMCP CLI 启动

```bash
# 启动 stdio 模式的服务器
fastmcp run app/api/mcp_routers/file_read_mcp_server.py:mcp

# 启动 HTTP 模式的服务器
fastmcp run app/api/mcp_routers/file_read_mcp_server.py:mcp --transport http --port 8000
```

### 3. 连接到 MCP 客户端

服务器启动后，可以连接到支持 MCP 协议的客户端，如：
- Claude Desktop
- VS Code with MCP extension
- 其他支持 MCP 的 AI 助手

#### HTTP 模式连接示例

```python
import asyncio
from fastmcp import Client

async def main():
    client = Client("http://localhost:8000")

    async with client:
        # 调用文件上传工具
        result = await client.call_tool("upload_files_by_stream", {
            "file_paths": ["/path/to/your/file.pdf"],
            "task_id": "example_task_001"
        })
        print(result)

        # 调用文件处理工具
        result = await client.call_tool("read_file_content_tool", {
            "task_id": "example_task_001",
            "purpose": "content_reading",
            "target_format": "plain_text",
            "enable_ocr": True
        })
        print(result)

asyncio.run(main())
```

## 工具使用示例

### 文件上传

```python
# 上传单个文件
await client.call_tool("upload_files_by_stream", {
    "file_paths": ["/path/to/document.pdf"],
    "task_id": "task_001",
    "priority": "HIGH"
})

# 上传多个文件
await client.call_tool("upload_files_by_stream", {
    "file_paths": ["/path/to/doc1.pdf", "/path/to/doc2.docx"],
    "task_id": "task_002"
})

# 上传文本内容
await client.call_tool("upload_text_content_tool", {
    "content": "这是要上传的文本内容...",
    "task_id": "task_003",
    "auto_detect": True
})
```

### 文件处理

```python
# 读取文件内容
await client.call_tool("read_file_content_tool", {
    "task_id": "task_001",
    "purpose": "content_reading",
    "target_format": "plain_text",
    "enable_ocr": True
})

# 文件切片
await client.call_tool("chunk_file_content_tool", {
    "task_id": "task_001",
    "chunk_size": 1000,
    "chunk_overlap": 100,
    "chunking_strategy": "recursive"
})

# 生成总结
await client.call_tool("summarize_file_content_tool", {
    "task_id": "task_001",
    "summary_length": "medium",
    "summary_focus": "主要内容概述"
})

# 信息抽取
await client.call_tool("extract_file_content_tool", {
    "task_id": "task_001",
    "purpose": "content_reading",
    "target_format": "plain_text",
    "enable_ocr": True
})
```

## 配置说明

### 传输模式

- **stdio**: 标准输入输出模式，适用于本地 MCP 客户端
- **http**: HTTP 模式，支持远程访问
- **sse**: Server-Sent Events 模式，支持实时通信

### 参数说明

- `--transport`: 指定传输模式 (stdio/http/sse)
- `--host`: HTTP/SSE 服务器主机地址 (默认: 127.0.0.1)
- `--port`: HTTP/SSE 服务器端口 (默认: 8000)
- `--log-level`: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)

## 错误处理

所有工具都包含完善的错误处理机制，当发生错误时会返回包含错误信息的 JSON 响应：

```json
{
  "error": "具体的错误信息描述"
}
```

## 开发说明

### 添加新工具

要在 MCP 服务器中添加新工具，请在 `file_read_mcp_server.py` 中：

1. 使用 `@mcp.tool()` 装饰器定义工具函数
2. 添加详细的文档字符串描述参数和返回值
3. 实现工具逻辑
4. 处理异常并返回适当的响应

### 工具命名约定

- 使用小写字母和下划线命名工具函数
- 工具名应该清晰描述其功能
- 参数名应该具有描述性

## 许可证

此项目遵循项目的许可证协议。