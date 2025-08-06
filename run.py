#!/usr/bin/env python3
"""
快速启动脚本
Quick Start Script
"""

import os
import sys
import subprocess
from pathlib import Path


def create_directories():
    """创建必要的目录"""
    directories = [
        "uploads",
        "temp", 
        "logs",
        "static/uploads",
        "static/css",
        "static/js"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录: {directory}")


def install_dependencies():
    """安装依赖包"""
    print("📦 安装依赖包...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ 依赖包安装完成")
    except subprocess.CalledProcessError:
        print("❌ 依赖包安装失败")
        return False
    return True


def create_env_file():
    """创建环境配置文件"""
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 创建环境配置文件...")
        env_content = """# 基础配置
DEBUG=true
HOST=0.0.0.0
PORT=8000

# 文件处理配置
MAX_FILE_SIZE=52428800
OCR_ENGINE=tesseract
DEFAULT_CHUNK_SIZE=1000

# 日志配置
LOG_LEVEL=INFO
"""
        env_file.write_text(env_content, encoding="utf-8")
        print("✅ 环境配置文件创建完成")


def main():
    """主函数"""
    print("🚀 初始化文件阅读系统...")
    
    # 创建目录
    create_directories()
    
    # 创建环境配置文件
    create_env_file()
    
    print("\n📋 设置完成！")
    print("\n🔧 下一步:")
    print("1. 安装依赖: pip install -r requirements.txt")
    print("2. 启动服务: python main.py")
    print("3. 访问文档: http://localhost:8000/docs")
    
    # 询问是否安装依赖
    try:
        install = input("\n是否现在安装依赖包？(y/n): ").lower().strip()
        if install in ['y', 'yes', '是']:
            if install_dependencies():
                print("\n🎉 系统初始化完成！")
                print("运行 'python main.py' 启动服务")
            else:
                print("\n❌ 初始化未完成，请手动安装依赖")
    except KeyboardInterrupt:
        print("\n\n👋 初始化已取消")


if __name__ == "__main__":
    main()