"""
健康检查路由
Health Check Routes
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
import psutil
import os

router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    timestamp: datetime
    version: str
    uptime: str
    system_info: dict


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """系统健康检查"""
    
    # 获取系统信息
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    system_info = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_total": f"{memory.total / (1024**3):.1f} GB",
        "memory_used": f"{memory.used / (1024**3):.1f} GB",
        "memory_percent": memory.percent,
        "disk_total": f"{disk.total / (1024**3):.1f} GB",
        "disk_used": f"{disk.used / (1024**3):.1f} GB",
        "disk_percent": (disk.used / disk.total) * 100,
        "upload_dir_exists": os.path.exists("uploads"),
        "temp_dir_exists": os.path.exists("temp")
    }
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        uptime="运行中",
        system_info=system_info
    )


@router.get("/ping")
async def ping():
    """简单的ping检查"""
    return {"message": "pong", "timestamp": datetime.now()}