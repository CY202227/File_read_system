#!/usr/bin/env python3
"""
临时测试脚本：验证level4_semantic_splitting的修复
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.vectorization.chunking import chunk_text


def test_level4_basic():
    """测试level4基本功能"""
    text = """
    这是第一个段落。包含一些内容。
    
    这是第二个段落。讨论不同的主题。这个主题与前面完全不同。
    
    这是第三个段落。又回到了第一个段落的主题。继续讨论相关内容。
    """
    
    # 测试不带buffer_size参数（向后兼容）
    result1 = chunk_text(
        text=text,
        enable_chunking=True,
        chunking_strategy_value="semantic_splitting",
        chunk_size=500,
        chunk_overlap=50,
        chunking_config={
            "semantic_splitting_config": {
                "similarity_threshold": 0.3
            }
        },
        ai_client=None,
    )
    
    # 测试带buffer_size参数
    result2 = chunk_text(
        text=text,
        enable_chunking=True,
        chunking_strategy_value="semantic_splitting",
        chunk_size=500,
        chunk_overlap=50,
        chunking_config={
            "semantic_splitting_config": {
                "similarity_threshold": 0.3,
                "buffer_size": 2
            }
        },
        ai_client=None,
    )
    
    print("测试1 (无buffer_size):")
    print(f"  chunks数量: {len(result1.get('chunks', []))}")
    for i, chunk in enumerate(result1.get('chunks', [])):
        print(f"  chunk{i+1}: {chunk[:50]}...")
    
    print("\n测试2 (buffer_size=2):")
    print(f"  chunks数量: {len(result2.get('chunks', []))}")
    for i, chunk in enumerate(result2.get('chunks', [])):
        print(f"  chunk{i+1}: {chunk[:50]}...")
    
    print("\n✅ 测试完成，无异常")
    return True


if __name__ == "__main__":
    test_level4_basic()
