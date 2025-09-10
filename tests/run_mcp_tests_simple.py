#!/usr/bin/env python3
"""
运行 MCP 服务器测试 - 简化版
Run MCP Server Tests - Simple Version
"""

import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    # 运行 MCP 相关的测试
    exit_code = pytest.main([
        "-v",  # 详细输出
        "-s",  # 显示 print 语句
        "--tb=short",  # 简短的错误回溯
        "tests/test_mcp_server.py::test_mcp_server_connection",  # 只运行连接测试
        "tests/test_mcp_server.py::test_list_mcp_tools",  # 只运行工具列表测试
        "--asyncio-mode=auto"  # 自动处理异步测试
    ])

    sys.exit(exit_code)
