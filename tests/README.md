# 单元测试说明

本目录包含OCR和模型功能的单元测试。

## 测试文件结构

```
tests/
├── unit/
│   ├── test_ocr_reader.py      # OCRReader 单元测试
│   ├── test_file_manager.py    # FileManager 单元测试
│   └── test_log_utils.py       # 日志工具单元测试
├── conftest.py                 # pytest 配置文件
└── README.md                   # 本文件
```

## 运行测试

### 1. 安装依赖

```bash
pip install pytest pytest-cov
```

### 2. 运行所有测试

```bash
# 从项目根目录运行
python run_tests.py

# 或者直接使用pytest
pytest tests/unit/ -v
```

### 3. 运行特定测试

```bash
# 运行OCR测试
pytest tests/unit/test_ocr_reader.py -v

# 运行FileManager测试
pytest tests/unit/test_file_manager.py -v

# 运行日志工具测试
pytest tests/unit/test_log_utils.py -v
```

### 4. 生成覆盖率报告

```bash
pytest tests/unit/ --cov=app --cov-report=html
```

## 测试内容

### OCRReader 测试

- ✅ 初始化测试
- ✅ 支持的扩展名测试
- ✅ PDF图像加载测试
- ✅ 图像OCR处理测试
- ✅ 错误处理测试
- ✅ 文件类型验证测试
- ✅ 大图像处理测试

### FileManager 测试

- ✅ 初始化测试
- ✅ 文件格式转换测试
- ✅ 目标格式转换测试
- ✅ 文本读取测试
- ✅ OCR集成测试
- ✅ 错误回退测试
- ✅ 表格精度设置测试

### 日志工具测试

- ✅ 日志消息构建测试
- ✅ 同步函数装饰器测试
- ✅ 异步函数装饰器测试
- ✅ 异常处理测试
- ✅ 函数元数据保留测试
- ✅ 复杂参数处理测试

## 测试特点

1. **Mock隔离**: 使用unittest.mock隔离外部依赖
2. **全面覆盖**: 覆盖正常流程和异常情况
3. **配置灵活**: 通过conftest.py提供测试配置
4. **易于维护**: 清晰的测试结构和文档

## 注意事项

1. 测试使用模拟的OCR服务，不会调用真实的API
2. 测试会自动创建必要的临时目录
3. 所有测试都是独立的，可以并行运行
4. 测试覆盖了主要的业务逻辑和错误处理

## 添加新测试

1. 在`tests/unit/`目录下创建新的测试文件
2. 遵循现有的测试命名规范
3. 使用适当的mock来隔离依赖
4. 添加详细的测试文档
5. 确保测试覆盖正常和异常情况
