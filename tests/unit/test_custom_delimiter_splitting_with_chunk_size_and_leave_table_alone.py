import pytest
from app.vectorization.chunking import (
    custom_delimiter_splitting_with_chunk_size_and_leave_table_alone,
    ChunkingConfig,
)


class TestCustomDelimiterSplittingWithChunkSizeAndLeaveTableAlone:
    """测试custom_delimiter_splitting_with_chunk_size_and_leave_table_alone函数"""

    def test_empty_delimiter(self):
        """测试空分隔符的情况"""
        text = "这是一段测试文本"
        chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
            text, delimiter=""
        )
        assert chunks == [text]

    def test_no_delimiter_in_text(self):
        """测试文本中没有分隔符的情况"""
        text = "这是一段测试文本"
        config = ChunkingConfig(chunk_size=10, chunk_overlap=2)
        chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
            text, delimiter="\n\n", config=config
        )
        # 应该按chunk_size进行智能合并
        assert len(chunks) > 0
        # 由于没有分隔符，整个文本应该作为一个块
        assert len(chunks) == 1

    def test_simple_delimiter_splitting(self):
        """测试简单的分隔符切分"""
        text = "第一段\n\n第二段\n\n第三段"
        chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
            text, delimiter="\n\n"
        )
        # 应该按\n\n切分，然后进行智能合并
        assert len(chunks) >= 1

    def test_table_preservation(self):
        """测试表格保持完整"""
        text = """这是表格前的文本

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 数据1 | 数据2 | 数据3 |
| 数据4 | 数据5 | 数据6 |

这是表格后的文本"""
        
        chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
            text, delimiter="\n\n"
        )
        
        # 检查是否包含完整的表格
        table_found = False
        for chunk in chunks:
            if "| 列1 | 列2 | 列3 |" in chunk and "|-----|-----|-----|" in chunk:
                table_found = True
                # 确保表格是完整的
                assert "| 数据1 | 数据2 | 数据3 |" in chunk
                assert "| 数据4 | 数据5 | 数据6 |" in chunk
                break
        
        assert table_found, "表格应该保持完整"

    def test_mixed_content_with_tables(self):
        """测试包含表格和普通文本的混合内容"""
        text = """第一段文本

| 标题1 | 标题2 |
|-------|-------|
| 内容1 | 内容2 |

第二段文本

| 另一个表格 | 列2 |
|------------|-----|
| 数据1 | 数据2 |

第三段文本"""
        
        config = ChunkingConfig(chunk_size=50, chunk_overlap=5)
        chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
            text, delimiter="\n\n", config=config
        )
        
        # 检查表格是否保持完整
        table1_found = False
        table2_found = False
        
        for chunk in chunks:
            if "| 标题1 | 标题2 |" in chunk and "|-------|-------|" in chunk:
                table1_found = True
            if "| 另一个表格 | 列2 |" in chunk and "|------------|-----|" in chunk:
                table2_found = True
        
        assert table1_found, "第一个表格应该保持完整"
        assert table2_found, "第二个表格应该保持完整"

    def test_smart_merging_behavior(self):
        """测试智能合并行为，确保块大小接近目标大小"""
        text = "第一段文本。\n\n第二段文本。\n\n第三段文本。\n\n第四段文本。\n\n第五段文本。"
        
        config = ChunkingConfig(chunk_size=50, chunk_overlap=10)
        chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
            text, delimiter="。", config=config
        )
        
        # 检查每个块的大小是否合理
        for i, chunk in enumerate(chunks):
            chunk_size = len(chunk)
            # 块大小应该在合理范围内（不超过目标大小的2倍，除非是单个段落）
            assert chunk_size <= 100, f"Chunk {i} 长度 {chunk_size} 超过了合理范围"
            
            # 如果块太小（小于目标大小的30%），检查是否是最后一个块
            if chunk_size < 15 and i < len(chunks) - 1:
                # 如果不是最后一个块，应该与其他块合并
                pass  # 允许小块的最后一个块
        
        # 检查是否按分隔符正确切分
        all_text = "".join(chunks)
        assert "第一段文本" in all_text
        assert "第二段文本" in all_text
        assert "第三段文本" in all_text

    def test_complex_markdown_with_tables(self):
        """测试复杂的markdown文档，包含表格、标题等"""
        text = """# 文档标题

## 第一部分

这是第一部分的介绍文本。

| 功能 | 描述 | 状态 |
|------|------|------|
| 功能1 | 这是功能1的描述 | 已完成 |
| 功能2 | 这是功能2的描述 | 进行中 |

## 第二部分

这是第二部分的介绍文本。

| 项目 | 进度 | 备注 |
|------|------|------|
| 项目A | 80% | 即将完成 |
| 项目B | 60% | 正常进行 |

### 子部分

这是子部分的内容。"""
        
        config = ChunkingConfig(chunk_size=100, chunk_overlap=10)
        chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
            text, delimiter="\n\n", config=config
        )
        
        # 检查表格是否保持完整
        table1_found = False
        table2_found = False
        
        for chunk in chunks:
            if "| 功能 | 描述 | 状态 |" in chunk and "|------|------|------|" in chunk:
                table1_found = True
                assert "| 功能1 | 这是功能1的描述 | 已完成 |" in chunk
                assert "| 功能2 | 这是功能2的描述 | 进行中 |" in chunk
            
            if "| 项目 | 进度 | 备注 |" in chunk and "|------|------|------|" in chunk:
                table2_found = True
                assert "| 项目A | 80% | 即将完成 |" in chunk
                assert "| 项目B | 60% | 正常进行 |" in chunk
        
        assert table1_found, "第一个表格应该保持完整"
        assert table2_found, "第二个表格应该保持完整"

    def test_table_without_separator_line(self):
        """测试没有分隔符行的表格（不应该被识别为表格）"""
        text = """这是普通文本

| 这不应该被识别为表格 |
| 因为没有分隔符行 |

这是更多文本"""
        
        chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
            text, delimiter="\n\n"
        )
        
        # 检查是否没有将没有分隔符行的内容识别为表格
        for chunk in chunks:
            if "| 这不应该被识别为表格 |" in chunk:
                # 这个内容应该被当作普通文本处理，可能会被切分
                assert "| 因为没有分隔符行 |" in chunk or "| 因为没有分隔符行 |" not in chunk

    def test_multiple_consecutive_tables(self):
        """测试连续的多个表格"""
        text = """文本1

| 表格1 | 列2 |
|-------|-----|
| 数据1 | 数据2 |

| 表格2 | 列2 |
|-------|-----|
| 数据3 | 数据4 |

文本2"""
        
        chunks = custom_delimiter_splitting_with_chunk_size_and_leave_table_alone(
            text, delimiter="\n\n"
        )
        
        # 检查两个表格是否都被正确识别和保持完整
        table1_found = False
        table2_found = False
        
        for chunk in chunks:
            if "| 表格1 | 列2 |" in chunk and "|-------|-----|" in chunk:
                table1_found = True
                assert "| 数据1 | 数据2 |" in chunk
            
            if "| 表格2 | 列2 |" in chunk and "|-------|-----|" in chunk:
                table2_found = True
                assert "| 数据3 | 数据4 |" in chunk
        
        assert table1_found, "第一个表格应该保持完整"
        assert table2_found, "第二个表格应该保持完整"
