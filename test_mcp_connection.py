#!/usr/bin/env python3
"""
测试 MCP 服务器连接
Test MCP Server Connection
"""

import asyncio
import json
from fastmcp import Client

async def test_mcp_connection():
    """测试 MCP 服务器连接"""
    print("🔍 测试 MCP 服务器连接...")

    try:
        # 连接到 MCP 服务器
        client = Client("http://127.0.0.1:8000/mcp")

        async with client:
            print("✅ 成功连接到 MCP 服务器")

            # 获取可用工具列表
            print("\n📋 获取可用工具列表...")
            tools = await client.list_tools()
            print(f"发现 {len(tools)} 个工具:")

            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")

            # 测试上传文本内容工具
            print("\n📝 测试上传文本内容工具...")
            test_content = "这是一个测试文档，用于验证 MCP 服务器的功能。\n\n包含两段内容：\n第一段是介绍。\n第二段是详细说明。"

            result = await client.call_tool("upload_text_content_tool", {
                "content": test_content,
                "task_id": "",
                "auto_detect": True
            })

            print("上传结果:")
            # 处理 FastMCP 的 CallToolResult 返回格式
            if hasattr(result, 'content') and result.content:
                if result.content[0].text:
                    print(json.dumps(json.loads(result.content[0].text), indent=2, ensure_ascii=False))
                else:
                    print("返回内容为空")
            else:
                print(f"未预期的返回格式: {type(result)}")

            # 等待一下让任务处理完成
            await asyncio.sleep(2)

            # 从上传结果中提取任务ID
            if hasattr(result, 'content') and result.content and result.content[0].text:
                upload_data = json.loads(result.content[0].text)
                task_id = upload_data.get("task_id")
                print(f"📋 使用任务ID: {task_id}")

                # 测试文件读取工具
                print("\n📖 测试文件读取工具...")
                result = await client.call_tool("read_file_content_tool", {
                    "task_id": task_id,
                    "purpose": "content_reading",
                    "target_format": "plain_text",
                    "enable_ocr": False
                })

            print("读取结果:")
            # 处理 FastMCP 的 CallToolResult 返回格式
            if hasattr(result, 'content') and result.content:
                if result.content[0].text:
                    print(json.dumps(json.loads(result.content[0].text), indent=2, ensure_ascii=False))
                else:
                    print("返回内容为空")
            else:
                print(f"未预期的返回格式: {type(result)}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print("\n🔧 故障排除建议:")
        print("1. 确保 MCP 服务器正在运行")
        print("2. 检查服务器地址是否正确 (http://127.0.0.1:8000/mcp)")
        print("3. 查看服务器日志以获取更多信息")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
