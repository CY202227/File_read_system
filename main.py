"""
文件阅读系统主入口文件
File Reading System Main Entry Point

支持多种文件格式读取、OCR识别、向量化切块等功能
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.api.routes import file_upload, file_process, health
from app.core.exceptions import setup_exception_handlers
from config.settings import settings
from config.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时的初始化
    print("🚀 文件阅读系统启动中...")
    
    # 创建必要的目录
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("temp", exist_ok=True)
    os.makedirs("static/uploads", exist_ok=True)
    
    print("📁 目录结构初始化完成")
    print(f"🌐 服务将在 http://localhost:{settings.PORT} 启动")
    
    yield
    
    # 关闭时的清理
    print("🛑 文件阅读系统正在关闭...")


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title="文件阅读系统 API",
        description="支持多种文件格式解析、OCR识别和向量化切块的文件处理系统",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 挂载静态文件
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # 注册路由
    app.include_router(health.router, prefix="/api/v1", tags=["健康检查"])
    app.include_router(file_upload.router, prefix="/api/v1", tags=["文件上传"])
    app.include_router(file_process.router, prefix="/api/v1", tags=["文件处理"])
    
    # 设置异常处理器
    setup_exception_handlers(app)
    
    return app


# 创建应用实例
app = create_app()


@app.get("/")
async def root():
    """根路径欢迎页面"""
    return {
        "message": "欢迎使用文件阅读系统 API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "features": [
            "多格式文件解析 (PDF, Word, Excel, 图片等)",
            "OCR 光学字符识别",
            "智能文本分块",
            "向量化预处理",
            "多种输出格式 (Markdown, DataFrame, JSON等)"
        ]
    }


if __name__ == "__main__":
    # 设置日志
    setup_logging()
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True
    )


