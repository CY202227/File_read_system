"""
任务管理路由
Task management routes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime

from app.core.task_manager import (
    task_manager,
    get_task_info,
    update_task_status,
    get_queue_status,
    TaskStatus
)
router = APIRouter(prefix="/api", tags=["任务管理"])


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """
    获取任务详情
    
    - **task_id**: 任务ID
    - 返回任务的详细信息
    """
    try:
        task_info = get_task_info(task_id)
        return {
            "success": True,
            "data": task_info
        }
    except HTTPException as e:
        return {
            "success": False,
            "error": e.detail,
            "status_code": e.status_code
        }


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000)
):
    """
    列出任务
    
    - **status**: 可选的任务状态过滤
    - **limit**: 返回数量限制
    - 返回任务列表
    """
    try:
        # 解析状态
        task_status = None
        if status:
            try:
                task_status = TaskStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的任务状态: {status}"
                )
        
        tasks = task_manager.list_tasks(status=task_status, limit=limit)
        return {
            "success": True,
            "data": {
                "tasks": tasks,
                "total": len(tasks)
            }
        }
    except HTTPException as e:
        return {
            "success": False,
            "error": e.detail,
            "status_code": e.status_code
        }


@router.get("/tasks/queue/status")
async def get_queue_status():
    """
    获取队列状态
    
    - 返回当前队列的统计信息
    """
    try:
        status = get_queue_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.put("/tasks/{task_id}/status")
async def update_task_status_route(
    task_id: str,
    status: str,
    error_message: Optional[str] = None
):
    """
    更新任务状态
    
    - **task_id**: 任务ID
    - **status**: 新状态
    - **error_message**: 错误信息（可选）
    """
    try:
        # 解析状态
        try:
            task_status = TaskStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的任务状态: {status}"
            )
        
        # 更新任务状态
        update_kwargs = {}
        if error_message:
            update_kwargs["error_message"] = error_message
        
        update_task_status(task_id, task_status, **update_kwargs)
        
        return {
            "success": True,
            "message": f"任务状态已更新为: {status}"
        }
    except HTTPException as e:
        return {
            "success": False,
            "error": e.detail,
            "status_code": e.status_code
        }


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    取消任务
    
    - **task_id**: 任务ID
    - 取消指定的任务
    """
    try:
        success = task_manager.cancel_task(task_id)
        if success:
            return {
                "success": True,
                "message": "任务已取消"
            }
        else:
            return {
                "success": False,
                "error": "无法取消任务，可能任务已完成或不存在"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/tasks/stats")
async def get_task_stats():
    """
    获取任务统计信息
    
    - 返回任务的统计信息
    """
    try:
        # 获取队列状态
        queue_status = get_queue_status()
        
        # 获取各状态的任务数量
        all_tasks = task_manager.list_tasks()
        status_counts = {}
        for task in all_tasks:
            status = task.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 计算总文件数和总大小
        total_files = sum(task.get("file_count", 0) for task in all_tasks)
        total_size = sum(task.get("total_size", 0) for task in all_tasks)
        
        stats = {
            "queue_status": queue_status,
            "status_counts": status_counts,
            "total_files": total_files,
            "total_size": total_size,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/tasks/cleanup")
async def cleanup_expired_tasks():
    """
    清理过期任务
    
    - 清理已完成且过期的任务
    """
    try:
        cleaned_count = task_manager.cleanup_expired_tasks()
        return {
            "success": True,
            "message": f"已清理 {cleaned_count} 个过期任务"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 