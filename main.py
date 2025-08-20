"""
文件阅读系统主入口文件
File Reading System Main Entry Point

支持多种文件格式读取、OCR识别、向量化切块等功能
"""

import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.api.routes import file_upload, file_process, health, task_management
from app.core.exceptions import setup_exception_handlers
from config.settings import settings
from config.logging_config import setup_logging, get_logger
from app.core.task_manager import task_manager


async def _periodic_cleanup_task(stop_event: asyncio.Event) -> None:
    """后台定时清理任务：每24小时执行一次，删除一周前完成任务的源文件。"""
    logger = get_logger(__name__)
    interval_seconds = 24 * 60 * 60 * 7  # 每周
    while not stop_event.is_set():
        try:
            result = task_manager.cleanup_uploaded_sources(older_than_days=7)
            logger.info(
                "weekly_cleanup result: tasks_scanned=%s tasks_matched=%s files_deleted=%s",
                result.get("tasks_scanned"),
                result.get("tasks_matched"),
                result.get("files_deleted"),
            )
        except Exception as e:
            logger.exception("weekly_cleanup error: %s", e)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时的初始化
    print("🚀 文件阅读系统启动中...")
    
    # 创建必要的目录
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("temp", exist_ok=True)
    os.makedirs("static/uploads", exist_ok=True)
    os.makedirs("static/ocr_temp", exist_ok=True)
    
    print("📁 目录结构初始化完成")
    print(f"🌐 服务将在 http://localhost:{settings.PORT} 启动")
    
    # 启动后台定时清理任务
    stop_event = asyncio.Event()
    cleanup_task = asyncio.create_task(_periodic_cleanup_task(stop_event))

    yield

    # 关闭时停止后台任务
    stop_event.set()
    try:
        await asyncio.wait_for(cleanup_task, timeout=5)
    except Exception:
        cleanup_task.cancel()
    
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
    app.include_router(task_management.router, prefix="/api/v1", tags=["任务管理"])
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
            "多种输出格式 (Markdown, DataFrame, JSON等)",
            "任务管理和队列系统"
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


