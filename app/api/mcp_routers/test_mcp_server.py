#!/usr/bin/env python3
"""
文件阅读系统 MCP 服务器测试脚本
File Reading System MCP Server Test Script

此脚本用于测试 MCP 服务器的功能。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from fastmcp import Client
    from config.logging_config import get_logger

    logger = get_logger(__name__)

except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖包: pip install -r requirements.txt")
    sys.exit(1)


async def test_mcp_tools():
    """测试 MCP 工具功能"""
    print("开始测试文件阅读系统 MCP 服务器...")

    # 连接到 MCP 服务器 (假设服务器运行在 http://localhost:8000)
    client = Client("http://localhost:8000")

    try:
        async with client:
            print("\n1. 测试上传文本内容工具...")

            # 测试上传文本内容
            result = await client.call_tool("upload_text_content_tool", {
                "content": "这是一个测试文档，包含一些基本信息。\n\n第一段：介绍文档的内容。\n第二段：详细说明文档的用途。",
                "task_id": "test_task_001",
                "auto_detect": True
            })

            print(f"上传结果: {result}")

            # 等待一下让任务处理完成
            await asyncio.sleep(2)

            print("\n2. 测试文件读取工具...")

            # 测试文件读取
            result = await client.call_tool("read_file_content_tool", {
                "task_id": "test_task_001",
                "purpose": "content_reading",
                "target_format": "plain_text",
                "enable_ocr": False
            })

            print(f"读取结果: {result}")

            print("\n3. 测试文件切片工具...")

            # 测试文件切片
            result = await client.call_tool("chunk_file_content_tool", {
                "task_id": "test_task_001",
                "chunk_size": 50,
                "chunk_overlap": 10,
                "chunking_strategy": "recursive"
            })

            print(f"切片结果: {result}")

            print("\n4. 测试文件总结工具...")

            # 测试文件总结
            result = await client.call_tool("summarize_file_content_tool", {
                "task_id": "test_task_001",
                "summary_length": "short",
                "summary_focus": "文档主要内容"
            })

            print(f"总结结果: {result}")

            print("\n5. 测试信息抽取工具...")

            # 测试信息抽取
            result = await client.call_tool("extract_file_content_tool", {
                "task_id": "test_task_001",
                "purpose": "content_reading",
                "target_format": "plain_text",
                "enable_ocr": False
            })

            print(f"抽取结果: {result}")

    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        print("请确保 MCP 服务器正在运行在 http://localhost:8000")
        print("启动命令: python app/api/mcp_routers/run_mcp_server.py --transport http --port 8000")


async def test_stdio_mode():
    """测试 stdio 模式的 MCP 服务器"""
    print("注意：stdio 模式需要特殊的测试方式，通常通过 MCP 客户端进行测试")
    print("推荐使用以下方式测试：")
    print("1. 启动 stdio 服务器: python app/api/mcp_routers/run_mcp_server.py")
    print("2. 使用 MCP 客户端连接测试")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试文件阅读系统 MCP 服务器")
    parser.add_argument(
        "--mode",
        choices=["http", "stdio"],
        default="http",
        help="测试模式"
    )
    parser.add_argument(
        "--server-url",
        default="http://localhost:8000",
        help="MCP 服务器 URL (仅在 http 模式下使用)"
    )

    args = parser.parse_args()

    if args.mode == "http":
        # 更新客户端 URL
        global client_url
        client_url = args.server_url
        asyncio.run(test_mcp_tools())
    else:
        test_stdio_mode()


if __name__ == "__main__":
    main()