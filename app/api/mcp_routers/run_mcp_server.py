#!/usr/bin/env python3
"""
文件阅读系统 MCP 服务器运行脚本
File Reading System MCP Server Runner

此脚本用于启动文件阅读系统的 MCP 服务器，提供文件上传和处理相关的工具。
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.api.mcp_routers.file_read_mcp_server import mcp
    from config.logging_config import get_logger

    logger = get_logger(__name__)

except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖包: pip install -r requirements.txt")
    sys.exit(1)


def main():
    """主函数，解析命令行参数并启动 MCP 服务器"""
    parser = argparse.ArgumentParser(
        description="文件阅读系统 MCP 服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 启动 stdio 模式的 MCP 服务器（默认）
  python run_mcp_server.py

  # 启动 HTTP 模式的 MCP 服务器
  python run_mcp_server.py --transport http --port 8001

  # 启动 SSE 模式的 MCP 服务器
  python run_mcp_server.py --transport sse --port 8002

  # 使用 fastmcp CLI 启动服务器
  fastmcp run app/api/mcp_routers/file_read_mcp_server.py:mcp

  # 使用 fastmcp CLI 启动 HTTP 服务器
  fastmcp run app/api/mcp_routers/file_read_mcp_server.py:mcp --transport http --port 8000
        """
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="MCP 服务器传输模式 (默认: stdio)"
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP/SSE 服务器主机地址 (默认: 127.0.0.1)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP/SSE 服务器端口 (默认: 8000)"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="日志级别 (默认: INFO)"
    )

    args = parser.parse_args()

    # 设置日志级别
    import logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    logger.info(f"启动文件阅读系统 MCP 服务器 (传输模式: {args.transport})")

    try:
        if args.transport == "stdio":
            # stdio 模式 - 直接运行
            logger.info("使用 stdio 传输模式启动服务器")
            mcp.run()

        elif args.transport == "http":
            # HTTP 模式
            logger.info(f"使用 HTTP 传输模式启动服务器，监听地址: {args.host}:{args.port}")
            mcp.run(transport="http", host=args.host, port=args.port)

        elif args.transport == "sse":
            # SSE 模式
            logger.info(f"使用 SSE 传输模式启动服务器，监听地址: {args.host}:{args.port}")
            mcp.run(transport="sse", host=args.host, port=args.port)

    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()