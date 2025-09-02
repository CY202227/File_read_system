# 文件阅读系统 (File Reading System)

一个支持多种文件格式读取、解析、OCR识别、向量化切块和智能处理的通用文件处理系统。用户可以上传任意文件，系统会根据用户需求输出不同格式的数据（如 Markdown、DataFrame、分块数据等）。

## 🏗️ 项目架构

### 📁 目录结构说明

```
file_read_system/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── file_upload.py          # 文件上传接口
│   │   │   ├── file_process.py         # 文件处理核心接口
│   │   │   ├── task_management.py      # 任务管理接口
│   │   │   └── health.py               # 健康检查接口
│   │   └── schemas/
│   │       ├── file_process_schemas.py # 文件处理数据模型
│   │       ├── file_read_schemas.py    # 文件读取数据模型
│   │       ├── file_chunk_schemas.py   # 文件切片数据模型
│   │       ├── file_summarize_schemas.py # 文件摘要数据模型
│   │       └── file_extract_schemas.py # 文件抽取数据模型
│   ├── core/
│   │   ├── exceptions.py               # 自定义异常类
│   │   ├── file_manager.py             # 文件管理
│   │   ├── job_manager.py              # 任务执行管理
│   │   └── task_manager.py             # 任务状态管理
│   ├── ai/
│   │   └── client.py                   # AI模型客户端
│   ├── embeddings/
│   │   └── provider.py                 # 向量模型提供者
│   ├── models/
│   │   └── provider.py                 # 大语言模型提供者
│   ├── ocr/
│   │   └── database.py                 # OCR数据库
│   ├── parsers/
│   │   └── converters/
│   │       ├── file_convert.py         # 文件格式转换
│   │       └── markdown_convert.py     # Markdown转换
│   ├── processors/
│   ├── utils/
│   │   └── file_utils.py               # 文件工具函数
│   └── vectorization/                  # 向量化相关模块
├── config/
│   ├── constants.py                    # 常量定义
│   ├── logging_config.py               # 日志配置
│   └── settings.py                     # 应用配置
├── docs/                               # API文档和示例
├── examples/                           # 使用示例
├── logs/                               # 日志文件
├── static/                             # 静态文件
├── templates/                          # 模板文件
├── uploads/                            # 上传文件存储
├── temp/                               # 临时文件
├── main.py                             # 主应用入口
├── run.py                              # 运行脚本
└── requirements.txt                    # 依赖包列表
```

## 🔧 各模块详细说明

### 📊 API 层 (`app/api/`)

- **routes/**: 定义 RESTful API 路由
  - `file_upload.py`: 文件上传接口，支持多文件上传和格式验证
  - `file_process.py`: 核心文件处理接口，支持多种处理模式
  - `task_management.py`: 任务状态查询和管理接口
  - `health.py`: 系统健康检查接口
- **schemas/**: 使用 Pydantic 定义请求/响应数据模型，包含完整的文件处理流程

### 🧠 核心业务层 (`app/core/`)

- **file_manager.py**: 管理文件的上传、存储、删除等操作
- **job_manager.py**: 任务执行引擎，协调各个处理步骤
- **task_manager.py**: 任务状态管理，支持任务创建、状态查询和清理
- **exceptions.py**: 定义系统自定义异常类

### 🤖 AI 模型层 (`app/ai/`, `app/models/`, `app/embeddings/`)

- **ai/client.py**: AI模型客户端，支持多种AI服务
- **models/provider.py**: 大语言模型提供者，支持Qwen3等模型
- **embeddings/provider.py**: 向量模型提供者，支持文本向量化

### 🔍 解析器层 (`app/parsers/`)

**职责**: 将不同格式的文件转换为统一的内部数据结构

- **converters/file_convert.py**: 核心文件转换器，支持多种格式
- **converters/markdown_convert.py**: Markdown格式转换器

### 👁️ OCR模块 (`app/ocr/`)

**职责**: 专门处理图像中的文字识别，支持多种OCR引擎

- **database.py**: OCR结果存储和管理

### ⚙️ 处理器层 (`app/processors/`)

**职责**: 对解析后的数据进行二次处理和优化

### 🧮 向量化模块 (`app/vectorization/`)

**职责**: 专门处理面向向量化的文本切块和预处理

### 📤 输出层 (`app/outputs/`)

**职责**: 将处理后的数据转换为用户需要的输出格式

### 🛠️ 工具层 (`app/utils/`)

- **file_utils.py**: 文件操作、格式检测、大小验证等
- **log_utils.py**: 日志记录工具

## 🚀 核心功能特性

### 📁 支持的文件格式

- **文档格式**: .pdf, .docx, .doc, .xlsx, .xls, .pptx, .ppt
- **特殊文档**: .ofd, .wps (需预转换)
- **文本格式**: .txt, .md, .csv, .tsv, .json, .xml
- **图像格式**: .jpg, .jpeg, .png, .tiff, .bmp, .webp (OCR支持)
- **代码格式**: .py, .js, .html, .css, .java, .cpp, .c, .go, .rs
- **音频文件**: .mp4, .mp3, .wav, .flac

### 📋 输出格式选项

- **plain_text**: 纯文本格式
- **markdown**: 格式化的Markdown文档
- **dataframe**: Pandas DataFrame格式
- **json**: 结构化JSON数据

### 🔧 处理功能

**智能分块**: 支持6个等级的分块策略
- **Level 1**: 字符分割 (Character Splitting)
- **Level 2**: 递归字符分割 (Recursive Character Splitting)
- **Level 3**: 文档特定分割 (Document Specific Splitting)
- **Level 4**: 语义分割 (Semantic Splitting)
- **Level 5**: 智能代理分割 (Agentic Splitting)
- **Level 6**: 自定义分隔符分割 (Custom Delimiter Splitting)
- **Level 6+**: 自定义分隔符分割并保持表格完整

**内容分析**: 支持多文件摘要生成，可配置摘要长度和焦点
**数据清洗**: 自动去除格式噪声、标准化文本
**批量处理**: 支持多文件并发处理
**进度跟踪**: 实时显示处理进度

## 💻 技术栈

### 后端框架
- **FastAPI**: 现代、高性能的Python Web框架
- **Uvicorn**: ASGI服务器
- **Pydantic**: 数据验证和序列化

### 文件处理库
- **pandas**: 数据处理和DataFrame操作
- **openpyxl**: Excel文件读写
- **python-docx**: Word文档处理
- **PyPDF2/pdfplumber**: PDF文档解析
- **markitdown**: 文件转Markdown处理
- **PyMuPDF**: PDF高级处理
- **chardet**: 字符编码检测

### AI和NLP相关库
- **spacy**: 自然语言处理，语义分析
- **nltk**: 自然语言工具包
- **openai**: OpenAI API支持
- **langextract**: Google信息抽取

### 其他工具库
- **aiofiles**: 异步文件操作
- **beautifulsoup4**: HTML解析
- **python-pptx**: PPTX解析
- **xmltodict**: XML解析
- **structlog**: 结构化日志
- **python-magic**: 文件类型检测

## 🔄 工作流程

### 标准处理流程

1. **文件上传** → 验证格式和大小
2. **格式识别** → 选择合适的解析器
3. **内容解析** → 提取文本和结构化数据
4. **数据处理** → 清洗、分析、转换
5. **格式输出** → 生成用户需要的格式
6. **结果返回** → 下载或在线预览

### 分块处理流程

1. **文本输入** → 已解析的纯文本内容
2. **分块策略选择** → 6个等级的分块方法
3. **智能切块** → 根据配置进行分块
4. **质量评估** → 评估分块效果
5. **切块输出** → 返回适合向量化的文本块数组

## ⚡ API 快速用法

### 核心接口

- **文件处理**: `POST /api/v1/file/process` - 完整的文件处理流程
- **文件读取**: `POST /api/v1/file/read` - 仅执行文件读取步骤
- **文件切片**: `POST /api/v1/file/chunk` - 执行文件切片步骤
- **文件摘要**: `POST /api/v1/file/summarize` - 生成文件摘要
- **信息抽取**: `POST /api/v1/file/extract` - 抽取特定信息

### 示例：语义切分 + 摘要 + 文本返回

```json
{
  "task_id": "task_xxx",
  "purpose": "content_reading",
  "target_format": "plain_text",
  "table_precision": 10,
  "enable_chunking": true,
  "chunking_strategy": "semantic_splitting",
  "chunk_size": 800,
  "chunk_overlap": 120,
  "chunking_config": {
    "semantic_splitting_config": {
      "similarity_threshold": 0.3
    }
  },
  "enable_multi_file_summary": true,
  "summary_length": 300,
  "summary_focus": ["main_points", "key_findings"],
  "summary_return_top_k": 5
}
```

### 自定义分隔符分块

```json
{
  "task_id": "task_xxx",
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

### 保持表格完整的分块

```json
{
  "task_id": "task_xxx",
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

## 🚀 快速开始

### 环境要求
- Python 3.8+
- 推荐使用虚拟环境

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置环境变量
创建 `.env` 文件并配置以下参数：
```bash
# AI模型配置
QWEN3_API_KEY=your_qwen3_api_key
QWEN3_MODEL_NAME=qwen3.5-14b-instruct
QWEN3_BASE_URL=your_qwen3_base_url

# 向量模型配置
EMBEDDING_MODEL=your_embedding_model
EMBEDDING_MODEL_URL=your_embedding_model_url
EMBEDDING_MODEL_API_KEY=your_embedding_api_key

# OCR配置
OCR_MODEL_URL=your_ocr_model_url
OCR_MODEL_API_KEY=your_ocr_api_key
OCR_MODEL_NAME=your_ocr_model_name

# 其他配置
OFD_API_URL=your_ofd_api_url
FULL_URL=your_full_url
```

### 启动服务
```bash
# 开发模式
python main.py

# 或使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 5015 --reload
```

### 访问API文档
- Swagger UI: http://localhost:5015/docs
- ReDoc: http://localhost:5015/redoc

## 📚 更多示例

查看 `docs/` 目录和 `examples/` 目录获取更多使用示例和API文档。

## 🛡️ 安全考虑

- 文件类型白名单验证
- 文件大小限制 (默认50MB)
- 临时文件自动清理 (7天)
- 访问权限控制
- 恶意文件扫描

## 🔧 配置说明

### 主要配置项
- **文件大小限制**: `MAX_FILE_SIZE` (默认50MB)
- **支持的文件格式**: `ALLOWED_EXTENSIONS`
- **分块设置**: `DEFAULT_CHUNK_SIZE`, `DEFAULT_CHUNK_OVERLAP`
- **任务超时**: `TASK_TIMEOUT` (默认5分钟)
- **服务器端口**: `PORT` (默认5015)

### 日志配置
- 日志级别: `LOG_LEVEL` (默认INFO)
- 日志文件: `logs/app.log`
- 支持结构化日志记录

## 📝 开发说明

### 代码质量
- 使用 `black` 进行代码格式化
- 使用 `flake8` 进行代码检查
- 使用 `mypy` 进行类型检查
- 使用 `pytest` 进行测试

### 测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/
pytest tests/integration/
```

### 日志
系统使用结构化日志记录，支持不同级别的日志输出，便于调试和监控。

---

这个架构设计具有高度的模块化和可扩展性，可以轻松添加新的文件格式支持和输出格式，同时保持代码的清晰和维护性。系统支持多种AI模型集成，提供智能化的文件处理能力。
