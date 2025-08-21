#!/usr/bin/env python3
"""
测试语义分割功能的脚本
"""

import json
from app.vectorization.chunking import chunk_text
from app.ai.client import AIClient

def test_semantic_chunking():
    """测试语义分割功能"""
    
    # 测试文本 - 包含明显的语义转换点
    test_text = """
    人工智能是计算机科学的一个分支。它试图理解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
    该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。
    
    机器学习是人工智能的核心。通过算法使机器能够从数据中学习并改进性能。
    深度学习作为机器学习的一个子领域，使用多层神经网络来模拟人脑的工作方式。
    
    在商业应用方面，人工智能正在改变各个行业。从医疗诊断到金融风控，从自动驾驶到智能客服。
    这些应用展示了人工智能的巨大潜力和价值。
    """
    
    print("=== 测试语义分割功能 ===")
    print(f"原始文本长度: {len(test_text)} 字符")
    print()
    
    # 测试参数
    test_cases = [
        {
            "name": "默认参数",
            "config": {
                "chunking_strategy_value": "semantic_splitting",
                "chunk_size": 800,
                "chunk_overlap": 120,
                "chunking_config": {
                    "semantic_splitting_config": {
                        "similarity_threshold": 0.25,
                        "buffer_size": 1
                    }
                }
            }
        },
        {
            "name": "更敏感的阈值",
            "config": {
                "chunking_strategy_value": "semantic_splitting", 
                "chunk_size": 800,
                "chunk_overlap": 120,
                "chunking_config": {
                    "semantic_splitting_config": {
                        "similarity_threshold": 0.2,
                        "buffer_size": 1
                    }
                }
            }
        },
        {
            "name": "更大的buffer_size",
            "config": {
                "chunking_strategy_value": "semantic_splitting",
                "chunk_size": 800, 
                "chunk_overlap": 120,
                "chunking_config": {
                    "semantic_splitting_config": {
                        "similarity_threshold": 0.2,
                        "buffer_size": 2
                    }
                }
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"--- 测试 {i}: {test_case['name']} ---")
        config = test_case['config']
        
        try:
            result = chunk_text(
                text=test_text,
                enable_chunking=True,
                chunking_strategy_value=config['chunking_strategy_value'],
                chunk_size=config['chunk_size'],
                chunk_overlap=config['chunk_overlap'],
                chunking_config=config['chunking_config'],
                ai_client=None  # 使用默认客户端
            )
            
            chunks = result.get('chunks', [])
            print(f"分割结果: {len(chunks)} 个chunks")
            
            for j, chunk in enumerate(chunks):
                print(f"  Chunk {j+1} ({len(chunk)} 字符): {chunk[:100]}...")
                
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
        
        print()

if __name__ == "__main__":
    test_semantic_chunking()
