"""
任务管理路由 - 基于temp目录JSON文件
Task management routes based on JSON files in temp directory
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from enum import Enum

router = APIRouter(tags=["任务管理"])

# temp目录路径
TEMP_DIR = Path("temp")


class TaskStatus(Enum):
    """任务状态枚举"""
    CREATED = "created"
    PENDING = "pending"
    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _get_task_json_path(task_id: str) -> Path:
    """获取任务JSON文件路径"""
    return TEMP_DIR / f"{task_id}.json"


def _load_task_from_json(task_id: str) -> Dict[str, Any]:
    """从JSON文件加载任务信息"""
    json_path = _get_task_json_path(task_id)
    
    if not json_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"任务不存在: {task_id}"
        )
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            task_data = json.load(f)
        return task_data
    except (json.JSONDecodeError, IOError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"读取任务文件失败: {str(e)}"
        )


def _save_task_to_json(task_id: str, task_data: Dict[str, Any]) -> None:
    """保存任务信息到JSON文件"""
    json_path = _get_task_json_path(task_id)
    
    # 确保temp目录存在
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # 原子写入：先写入临时文件，再替换
        tmp_path = json_path.with_suffix(json_path.suffix + ".tmp")
        payload = json.dumps(task_data, ensure_ascii=False, indent=2, default=str)
        with open(str(tmp_path), 'w', encoding='utf-8', newline='\n') as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(json_path))
    except IOError as e:
        raise HTTPException(
            status_code=500,
            detail=f"保存任务文件失败: {str(e)}"
        )


def _list_all_task_files() -> List[Path]:
    """列出所有任务JSON文件"""
    if not TEMP_DIR.exists():
        return []
    
    return list(TEMP_DIR.glob("*.json"))


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """
    获取任务详情
    
    - **task_id**: 任务ID
    - 返回任务的详细信息
    """
    try:
        task_info = _load_task_from_json(task_id)
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
        
        # 获取所有任务文件
        task_files = _list_all_task_files()
        tasks = []
        
        for task_file in task_files:
            try:
                task_id = task_file.stem  # 去掉.json扩展名
                task_data = _load_task_from_json(task_id)
                
                # 状态过滤
                if task_status is None or task_data.get("status") == task_status.value:
                    tasks.append(task_data)
            except Exception as e:
                # 跳过损坏的文件
                continue
        
        # 按创建时间排序
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "success": True,
            "data": {
                "tasks": tasks[:limit],
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
        task_files = _list_all_task_files()
        status_counts = {}
        total_tasks = 0
        
        for task_file in task_files:
            try:
                task_id = task_file.stem
                task_data = _load_task_from_json(task_id)
                status = task_data.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
                total_tasks += 1
            except Exception:
                continue
        
        status = {
            "total_tasks": total_tasks,
            "status_counts": status_counts,
            "pending_count": status_counts.get("pending", 0),
            "active_count": status_counts.get("active", 0) + status_counts.get("processing", 0),
            "completed_count": status_counts.get("completed", 0),
            "failed_count": status_counts.get("failed", 0),
            "cancelled_count": status_counts.get("cancelled", 0)
        }
        
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
        
        # 加载现有任务数据
        task_data = _load_task_from_json(task_id)
        
        # 更新状态
        task_data["status"] = task_status.value
        task_data["updated_at"] = datetime.now().isoformat()
        
        # 根据状态更新相应字段
        if task_status == TaskStatus.ACTIVE:
            task_data["started_at"] = datetime.now().isoformat()
        elif task_status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task_data["completed_at"] = datetime.now().isoformat()
        
        # 更新错误信息
        if error_message:
            task_data["error_message"] = error_message
        
        # 保存更新后的数据
        _save_task_to_json(task_id, task_data)
        
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
async def delete_task(task_id: str):
    """
    删除任务
    
    - **task_id**: 任务ID
    - 删除指定的任务文件
    """
    try:
        json_path = _get_task_json_path(task_id)
        
        if not json_path.exists():
            return {
                "success": False,
                "error": "任务不存在"
            }
        
        # 删除文件
        json_path.unlink()
        
        return {
            "success": True,
            "message": "任务已删除"
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
        task_files = _list_all_task_files()
        status_counts = {}
        total_files = 0
        total_size = 0
        
        for task_file in task_files:
            try:
                task_id = task_file.stem
                task_data = _load_task_from_json(task_id)
                
                # 统计状态
                status = task_data.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # 统计文件信息
                total_files += task_data.get("file_count", 0)
                total_size += task_data.get("total_size", 0)
                
            except Exception:
                continue
        
        stats = {
            "status_counts": status_counts,
            "total_files": total_files,
            "total_size": total_size,
            "total_tasks": len(task_files),
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
async def cleanup_completed_tasks():
    """
    清理已完成任务
    
    - 清理已完成、失败或取消的任务文件
    """
    try:
        task_files = _list_all_task_files()
        cleaned_count = 0
        
        for task_file in task_files:
            try:
                task_id = task_file.stem
                task_data = _load_task_from_json(task_id)
                
                # 检查是否应该清理
                status = task_data.get("status")
                if status in ["completed", "failed", "cancelled"]:
                    task_file.unlink()
                    cleaned_count += 1
                    
            except Exception:
                # 如果文件损坏，也删除它
                task_file.unlink()
                cleaned_count += 1
        
        return {
            "success": True,
            "message": f"已清理 {cleaned_count} 个任务文件"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/tasks/search")
async def search_tasks(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=200)
):
    """
    搜索任务
    
    - **keyword**: 搜索关键词（在任务ID、文件名等中搜索）
    - **status**: 状态过滤
    - **limit**: 返回数量限制
    """
    try:
        task_files = _list_all_task_files()
        results = []
        
        for task_file in task_files:
            try:
                task_id = task_file.stem
                task_data = _load_task_from_json(task_id)
                
                # 状态过滤
                if status and task_data.get("status") != status:
                    continue
                
                # 关键词搜索
                if keyword:
                    search_text = f"{task_id} {json.dumps(task_data, ensure_ascii=False)}"
                    if keyword.lower() not in search_text.lower():
                        continue
                
                results.append(task_data)
                
            except Exception:
                continue
        
        # 按创建时间排序
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "success": True,
            "data": {
                "tasks": results[:limit],
                "total": len(results)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 