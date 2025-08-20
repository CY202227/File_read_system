#!/usr/bin/env python3
"""
示例：使用 custom_delimiter_splitting_with_chunk_size_and_leave_table_alone 方法

这个示例展示了如何使用新的切块方法，该方法会：
1. 按自定义分隔符切分文本
2. 保持 markdown 表格完整
3. 对其他文本根据 chunk_size 和 overlap 进行窗口化处理
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.vectorization.chunking import (
    custom_delimiter_splitting_with_chunk_size_and_leave_table_alone,
    ChunkingConfig,
)


def main():
    # 示例文本，包含普通文本和 markdown 表格
    sample_text = """# 项目文档

## 功能概述

这是一个示例项目，展示了新的文本切块功能。

## 功能列表

| 功能名称 | 描述 | 状态 | 优先级 |
|----------|------|------|--------|
| 文本切块 | 支持多种切块策略 | 已完成 | 高 |
| 表格保持 | 保持 markdown 表格完整 | 已完成 | 高 |
| 语义分析 | 基于 AI 的语义切分 | 开发中 | 中 |

## 技术架构

项目采用模块化设计，主要包含以下组件：

| 组件 | 技术栈 | 版本 |
|------|--------|------|
| 后端 | Python | 3.13 |
| 前端 | React | 18.0 |
| 数据库 | PostgreSQL | 15.0 |

## 总结

这个项目展示了如何在不破坏表格结构的情况下进行文本切块。
"""

    print("原始文本:")
    print("=" * 50)
    print(sample_text)
    print("=" * 50)
    print()

    # 配置切块参数
    config = ChunkingConfig(
        chunk_size=100,  # 每个块最大100个字符
        chunk_overlap=20  # 相邻块重叠20个字符
    )

    # 使用新的切块方法
    chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
        text=sample_text,
        delimiter="\n\n",  # 按双换行符切分
        config=config
    )

    print(f"切块结果 (共 {len(chunks)} 个块):")
    print("=" * 50)
    
    for i, chunk in enumerate(chunks, 1):
        print(f"块 {i} (长度: {len(chunk)}):")
        print("-" * 30)
        print(chunk)
        print("-" * 30)
        print()

    # 分析结果
    print("分析结果:")
    print("=" * 50)
    
    table_chunks = []
    text_chunks = []
    
    for i, chunk in enumerate(chunks):
        if "|" in chunk and "|-----|" in chunk:
            table_chunks.append(i + 1)
        else:
            text_chunks.append(i + 1)
    
    print(f"表格块: {table_chunks}")
    print(f"文本块: {text_chunks}")
    print(f"表格保持完整: {'是' if len(table_chunks) == 2 else '否'}")


if __name__ == "__main__":
    main()
