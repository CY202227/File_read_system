#!/usr/bin/env python3
"""
示例：演示 custom_delimiter_splitting_with_chunk_size_and_leave_table_alone 的智能合并功能

这个示例展示了新的切块方法如何智能合并文本段落，确保每块尽可能接近目标大小。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.vectorization.chunking import (
    custom_delimiter_splitting_with_chunk_size_and_leave_table_alone,
    ChunkingConfig,
)


def main():
    # 示例文本，包含多个段落和表格
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

## 详细说明

这是第一段详细说明，包含了项目的背景和目标。

这是第二段详细说明，描述了项目的技术选型和架构设计。

这是第三段详细说明，说明了项目的开发计划和里程碑。

这是第四段详细说明，总结了项目的预期成果和影响。

这是第五段详细说明，提供了项目的联系方式和支持信息。"""

    print("原始文本:")
    print("=" * 50)
    print(sample_text)
    print("=" * 50)
    print()

    # 配置切块参数 - 目标大小1000字符
    config = ChunkingConfig(
        chunk_size=1000,  # 每个块目标1000个字符
        chunk_overlap=100  # 相邻块重叠100个字符
    )

    # 使用新的切块方法
    chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
        text=sample_text,
        delimiter="\n\n",  # 按双换行符切分
        config=config
    )

    print(f"切块结果 (共 {len(chunks)} 个块):")
    print("=" * 50)
    
    total_chars = 0
    for i, chunk in enumerate(chunks, 1):
        chunk_size = len(chunk)
        total_chars += chunk_size
        print(f"块 {i} (长度: {chunk_size}):")
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
    print(f"总字符数: {total_chars}")
    print(f"平均块大小: {total_chars / len(chunks):.1f}")
    
    # 分析块大小分布
    chunk_sizes = [len(chunk) for chunk in chunks]
    print(f"块大小分布: {chunk_sizes}")
    print(f"最大块大小: {max(chunk_sizes)}")
    print(f"最小块大小: {min(chunk_sizes)}")
    
    # 检查是否接近目标大小
    target_size = 1000
    close_to_target = sum(1 for size in chunk_sizes if 0.5 * target_size <= size <= 1.5 * target_size)
    print(f"接近目标大小({target_size})的块数: {close_to_target}/{len(chunks)}")


if __name__ == "__main__":
    main()
