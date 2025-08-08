# 文件阅读系统 (File Reading System)

一个支持多种文件格式读取、解析和格式化输出的通用文件处理系统。用户可以上传任意文件，系统会根据用户需求输出不同格式的数据（如 Markdown、DataFrame、分块数据等）。

## 🏗️ 项目架构

### 📁 目录结构说明

```
file_read_system/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── file_upload.py
│   │   │   ├── health.py
│   │   │   └── task_management.py
│   │   └── schemas/
│   │       ├── upload.py
│   │       └── file_process_schemas.py
│   ├── core/
│   │   ├── exceptions.py
│   │   ├── file_manager.py
│   │   ├── job_manager.py
│   │   └── task_manager.py
│   ├── ocr/
│   │   └── database.py
│   ├── parsers/
│   │   └── converters/
│   │       ├── file_convert.py
│   │       └── markdown_convert.py
│   ├── processors/
│   ├── utils/
│   │   └── file_utils.py
│   └── vectorization/
│       └── __init__.py
├── config/
│   ├── logging_config.py
│   └── settings.py
├── docs/
├── logs/
├── static/
├── templates/
├── uploads/
├── temp/
├── main.py
├── run.py
└── requirements.txt
```

## 🔧 各模块详细说明

### 📊 API 层 (`app/api/`)

- **routes/**: 定义 RESTful API 路由，包括文件上传、处理状态查询、结果下载等接口
- **middleware/**: 请求中间件，处理认证、限流、CORS 等
- **schemas/**: 使用 Pydantic 定义请求/响应数据模型

### 🧠 核心业务层 (`app/core/`)

- **file_manager.py**: 管理文件的上传、存储、删除等操作
- **task_queue.py**: 异步任务队列，处理大文件的后台解析任务
- **exceptions.py**: 定义系统自定义异常类

### 🔍 解析器层 (`app/parsers/`)

**职责**: 将不同格式的文件转换为统一的内部数据结构

- **base_parser.py**: 解析器抽象基类，定义统一接口
- **text_parser.py**: 处理纯文本、Markdown、CSV 等文本格式
- **office_parser.py**: 解析 Word、Excel、PowerPoint 文档
- **pdf_parser.py**: 提取 PDF 文档的文本和元数据
- **image_parser.py**: 调用OCR模块处理图像文件，提取文本内容
- **code_parser.py**: 解析各种编程语言源代码文件
- **binary_parser.py**: 处理二进制文件的元数据提取

### 👁️ OCR模块 (`app/ocr/`)

**职责**: 专门处理图像中的文字识别，支持多种OCR引擎

- **base_ocr.py**: OCR引擎抽象基类，定义统一的OCR接口

### ⚙️ 处理器层 (`app/processors/`)

**职责**: 对解析后的数据进行二次处理和优化

- **chunker.py**: 基础文本分块，支持按段落、句子、字符数等方式切分
- **analyzer.py**: 内容分析，提取关键词、摘要、统计信息等
- **cleaner.py**: 数据清洗，去除噪声、格式化文本等
- **transformer.py**: 数据格式转换和结构化处理

### 🧮 向量化模块 (`app/vectorization/`)

**职责**: 专门处理面向向量化的文本切块和预处理（不包含实际向量化）

- **semantic_chunker.py**: 语义感知的智能分块器，保持语义完整性
- **chunk_optimizer.py**: 分块优化器，调整分块大小和重叠度
- **embedding_prep.py**: 向量化预处理，为后续embedding做准备
- **chunk_strategies.py**: 多种分块策略（固定长度、滑动窗口、语义边界等）
- **chunk_evaluator.py**: 分块质量评估器，评估分块效果

### 📤 输出层 (`app/outputs/`)

**职责**: 将处理后的数据转换为用户需要的输出格式

- **markdown_output.py**: 生成格式化的 Markdown 文档
- **dataframe_output.py**: 输出 Pandas DataFrame 或 CSV 格式
- **json_output.py**: 生成结构化的 JSON 数据
- **excel_output.py**: 创建 Excel 工作簿
- **custom_output.py**: 支持用户自定义输出格式

### 🛠️ 工具层 (`app/utils/`)

- **file_utils.py**: 文件操作、格式检测、大小验证等
- **validation.py**: 输入参数验证和数据校验
- **logging.py**: 结构化日志记录
- **helpers.py**: 通用辅助函数

## 🚀 核心功能特性

### 📁 支持的文件格式

- **文本文件**: .txt, .md, .csv, .tsv
- **Office 文档**: .docx, .xlsx, .pptx
- **PDF 文档**: .pdf
- **图像文件**: .jpg, .png, .tiff (OCR)
- **代码文件**: .py, .js, .java, .cpp, .html 等
- **其他格式**: 可扩展支持

### 📋 输出格式选项

- **Markdown**: 格式化文档，支持表格、列表、代码块
- **DataFrame**: Pandas DataFrame 或 CSV 格式
- **JSON**: 结构化数据输出
- **Excel**: 多工作表 Excel 文件
- **分块输出**: 按指定规则切分的文本块
- **自定义格式**: 根据用户需求定制

### 🔧 处理功能

- **智能分块**: 按语义、段落或固定长度分割
- **内容分析**: 关键词提取、摘要生成
- **数据清洗**: 去除格式噪声、标准化文本
- **批量处理**: 支持多文件并发处理
- **进度跟踪**: 实时显示处理进度

## 💻 技术栈建议

### 后端框架

- **FastAPI**: 现代、高性能的 Python Web 框架
- **Celery**: 分布式任务队列
- **Redis**: 缓存和任务队列存储

### 文件处理库

- **pandas**: 数据处理和 DataFrame 操作
- **openpyxl**: Excel 文件读写
- **python-docx**: Word 文档处理
- **PyPDF2/pdfplumber**: PDF 文档解析
- **chardet**: 字符编码检测

### OCR 相关库

- **pytesseract**: Tesseract OCR Python 封装
- **PaddleOCR**: 百度开源的高精度OCR工具
- **Pillow (PIL)**: 图像处理和预处理
- **opencv-python**: 图像预处理和增强
- **easyocr**: 简单易用的OCR库
- **云端OCR SDK**: 百度、腾讯、阿里云、Azure等

### 向量化切块相关库

- **spacy**: 自然语言处理，语义分析
- **nltk**: 自然语言工具包，句子分割
- **langchain**: 文本分块和向量化工具链
- **tiktoken**: OpenAI的tokenizer，精确计算token数
- **sentence-transformers**: 语义相似度计算（用于分块质量评估）

### 数据库

- **SQLite/PostgreSQL**: 元数据存储
- **MinIO/S3**: 文件对象存储

### 前端 (可选)

- **Vue.js/React**: 用户界面
- **Element Plus/Ant Design**: UI 组件库

## 🔄 工作流程

### 标准处理流程

1. **文件上传** → 验证格式和大小
2. **格式识别** → 选择合适的解析器
3. **内容解析** → 提取文本和结构化数据
4. **数据处理** → 清洗、分析、转换
5. **格式输出** → 生成用户需要的格式
6. **结果返回** → 下载或在线预览

### OCR 处理流程

1. **图像上传** → 格式验证（jpg, png, tiff等）
2. **图像预处理** → 去噪、增强、校正（`ocr/preprocessor.py`）
3. **OCR引擎选择** → 根据语言和精度要求选择引擎
4. **文字识别** → 提取文本内容和坐标信息
5. **结果后处理** → 置信度过滤、文本矫正（`ocr/postprocessor.py`）
6. **文本输出** → 返回结构化文本数据

### 向量化切块流程

1. **文本输入** → 已解析的纯文本内容
2. **分块策略选择** → 固定长度/语义边界/滑动窗口等
3. **语义分析** → 识别段落、句子边界，保持语义完整性
4. **智能切块** → 根据token限制和重叠度进行分块
5. **质量评估** → 评估分块效果和语义连贯性
6. **切块输出** → 返回适合向量化的文本块数组

## 🛡️ 安全考虑

- 文件类型白名单验证
- 文件大小限制
- 恶意文件扫描
- 临时文件自动清理
- 访问权限控制

这个架构设计具有高度的模块化和可扩展性，可以轻松添加新的文件格式支持和输出格式，同时保持代码的清晰和维护性。
