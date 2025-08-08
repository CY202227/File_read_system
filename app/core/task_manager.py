"""
任务管理器
Task Manager for managing task IDs, states and queues
"""

import uuid
import time
import os
import json
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from enum import Enum
from fastapi import HTTPException
from pathlib import Path


class TaskStatus(Enum):
    """任务状态枚举"""
    CREATED = "created"
    PENDING = "pending"
    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskManager:
    """任务管理器类"""
    
    def __init__(self):
        # 配置（存储完全基于JSON文件，不使用内存存储）
        self._max_concurrent_tasks = 10
        self._task_timeout = 3600  # 1小时超时
        self._cleanup_interval = 300  # 5分钟清理一次
        self._last_cleanup = time.time()
        self._uploads_dir = "uploads"  # 上传目录
        self._temp_dir = Path("temp")  # temp目录
        
        # 确保temp目录存在
        self._temp_dir.mkdir(exist_ok=True)

    # ---------------- 文件队列/并发（基于JSON） ----------------
    def _count_active_from_fs(self) -> int:
        """统计当前active/processing任务数量（读取JSON文件）。"""
        count = 0
        for p in self._temp_dir.glob("*.json"):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            status = obj.get("status")
            if status in {TaskStatus.ACTIVE.value, TaskStatus.PROCESSING.value}:
                count += 1
        return count

    def _decide_initial_status_fs(self) -> str:
        """根据并发上限返回初始状态（active 或 pending）。"""
        return (
            TaskStatus.ACTIVE.value
            if self._count_active_from_fs() < self._max_concurrent_tasks
            else TaskStatus.PENDING.value
        )

    # ---------------- JSON 驱动的创建/更新/查询 ----------------
    def create_task_from_request(self, task_id: str, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        """创建任务JSON，保存完整入参到文件系统（队列采用JSON管理）。

        TODO: 后续保留对接数据库的实现（落库与回放）。
        """
        # 若任务已存在，则仅更新 request 等字段，避免覆盖已写入的 files 等信息
        json_path = self._get_task_json_path(task_id)
        if json_path.exists():
            try:
                existing = self._load_task_from_json(task_id)
            except Exception:
                existing = {}
            existing["request"] = request_dict
            existing["updated_at"] = datetime.now()
            # 如果之前标记为 completed/failed/cancelled，则重新进入 active/pending
            if existing.get("status") in {
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value,
            }:
                existing["status"] = self._decide_initial_status_fs()
                existing["started_at"] = None
                existing["completed_at"] = None
                existing["errors"] = None
            self._save_task_to_json(task_id, existing)
            return existing

        # 不存在则创建新文档
        doc: Dict[str, Any] = {
            "task_id": task_id,
            "status": self._decide_initial_status_fs(),
            "queue": "json",
            "max_concurrency": self._max_concurrent_tasks,
            "request": request_dict,
            "progress": {"percent": 0.0},
            "result": {"url": None, "data": None},
            "sections": {
                "upload_file_json": {},
                "process_json": {},
            },
            "events": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "errors": None,
        }
        self._save_task_to_json(task_id, doc)
        return doc

    def update_section(self, task_id: str, section: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """更新指定分段（如 upload_file_json）并保存到JSON。"""
        doc = self._load_task_from_json(task_id)
        sections = doc.get("sections") or {}
        current = sections.get(section) or {}
        if not isinstance(current, dict):
            current = {}
        current.update(payload)
        sections[section] = current
        doc["sections"] = sections
        doc["updated_at"] = datetime.now()
        self._save_task_to_json(task_id, doc)
        return doc

    def append_event(self, task_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """附加一条事件（供调试或SSE）。"""
        doc = self._load_task_from_json(task_id)
        events = doc.get("events") or []
        event = {
            **event,
            "time": datetime.now().isoformat(),
            "seq": len(events) + 1,
        }
        events.append(event)
        doc["events"] = events
        doc["updated_at"] = datetime.now()
        self._save_task_to_json(task_id, doc)
        return doc

    def get_status_from_json(self, task_id: str) -> Dict[str, Any]:
        """读取任务JSON并返回 FileProcessResponse 兼容结构。"""
        doc = self._load_task_from_json(task_id)
        result = doc.get("result") or {}
        sections = doc.get("sections") or {}
        return {
            "task_id": doc.get("task_id"),
            "status": doc.get("status"),
            "progress": (doc.get("progress") or {}).get("percent"),
            "result_url": result.get("url"),
            "result_data": result.get("data"),
            "processing_time": None,  # TODO: 由处理流程写入耗时
            "file_info": sections.get("upload_file_json"),
            "error_message": (doc.get("errors") or {}).get("message") if doc.get("errors") else None,
            "error_details": doc.get("errors"),
        }
    
    def _get_task_json_path(self, task_id: str) -> Path:
        """获取任务JSON文件路径"""
        return self._temp_dir / f"{task_id}.json"
    
    def _save_task_to_json(self, task_id: str, task_info: Dict) -> None:
        """保存任务信息到JSON文件"""
        json_path = self._get_task_json_path(task_id)
        # 确保 temp 目录存在
        self._temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 转换datetime对象为字符串
            task_data = task_info.copy()
            for key, value in task_data.items():
                if isinstance(value, datetime):
                    task_data[key] = value.isoformat()
            # 先写入临时文件，再原子替换，避免并发或句柄问题
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
    
    def _load_task_from_json(self, task_id: str) -> Dict:
        """从JSON文件加载任务信息"""
        json_path = self._get_task_json_path(task_id)
        
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
    
    def _check_task_exists_in_filesystem(self, task_id: str) -> bool:
        """
        检查任务在文件系统中是否存在
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 任务是否存在
        """
        json_path = self._get_task_json_path(task_id)
        return json_path.exists()
    
    def _check_task_exists_in_db(self, task_id: str) -> bool:
        """
        检查任务在数据库中是否存在（预留接口）
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 任务是否存在
        """
        # TODO: 实现数据库检查逻辑
        # return self._query_task_in_db(task_id) is not None
        return False
    
    def create_task(self, task_id: Optional[str] = None, priority: TaskPriority = TaskPriority.NORMAL, 
                   metadata: Optional[Dict] = None) -> str:
        """
        创建新任务
        
        Args:
            task_id: 可选的任务ID，如果不提供将自动生成
            priority: 任务优先级
            metadata: 任务元数据
            
        Returns:
            str: 任务ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        # 检查任务ID是否已存在（文件系统或数据库）
        if self._check_task_exists_in_filesystem(task_id):
            raise HTTPException(status_code=400, detail=f"任务ID已存在: {task_id}")
        if self._check_task_exists_in_db(task_id):
            raise HTTPException(status_code=400, detail=f"任务ID已存在(数据库): {task_id}")

        # 创建新任务（文件）
        initial_status = self._decide_initial_status_fs()
        task_info = {
            "task_id": task_id,
            "status": initial_status,
            "priority": priority.value,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "started_at": None,
            "completed_at": None,
            "files": [],
            "file_count": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
            "total_size": 0,
            "error_message": None,
            "metadata": metadata or {},
            "retry_count": 0,
            "max_retries": 3,
            "sections": {
                "upload_file_json": {},
                "process_json": {},
            },
            "result": {"url": None, "data": None},
            "progress": {"percent": 0.0},
            "events": [],
        }

        self._save_task_to_json(task_id, task_info)
        return task_id
    
    def validate_task(self, task_id: str) -> bool:
        """
        验证任务ID是否存在且有效
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 任务是否存在且有效
        """
        # 仅检查文件系统（不使用内存）
        if self._check_task_exists_in_filesystem(task_id):
            try:
                task_data = self._load_task_from_json(task_id)
                # 检查任务是否已过期
                if task_data.get("status") in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                    return False
                return True
            except Exception:
                return False
        
        # 最后检查数据库（预留）
        if self._check_task_exists_in_db(task_id):
            return True
        
        return False
    
    def get_task(self, task_id: str) -> Dict:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 任务信息
            
        Raises:
            HTTPException: 任务不存在
        """
        if self._check_task_exists_in_filesystem(task_id):
            return self._load_task_from_json(task_id)
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    def update_task_status(self, task_id: str, status: TaskStatus, **kwargs) -> None:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            **kwargs: 其他更新字段
            
        Raises:
            HTTPException: 任务不存在
        """
        # 验证task_id不为空
        if not task_id or task_id.strip() == '':
            raise HTTPException(
                status_code=400,
                detail="任务ID不能为空"
            )
        
        if not self._check_task_exists_in_filesystem(task_id):
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        task = self._load_task_from_json(task_id)
        task["status"] = status.value
        task["updated_at"] = datetime.now()

        # 根据状态更新相应字段
        if status == TaskStatus.ACTIVE:
            task["started_at"] = datetime.now()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task["completed_at"] = datetime.now()

        # 更新其他字段
        task.update(kwargs)

        # 保存到JSON文件
        self._save_task_to_json(task_id, task)
    
    def add_file_to_task(self, task_id: str, file_info: Dict) -> None:
        """
        向任务添加文件信息
        
        Args:
            task_id: 任务ID
            file_info: 文件信息
            
        Raises:
            HTTPException: 任务不存在
        """
        # 验证task_id不为空
        if not task_id or task_id.strip() == '':
            raise HTTPException(
                status_code=400,
                detail="任务ID不能为空"
            )
        
        if not self._check_task_exists_in_filesystem(task_id):
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        task = self._load_task_from_json(task_id)
        task.setdefault("files", []).append(file_info)
        task["file_count"] = len(task["files"])
        task["updated_at"] = datetime.now()

        if file_info.get("status") == "success":
            task["successful_uploads"] = task.get("successful_uploads", 0) + 1
            task["total_size"] = task.get("total_size", 0) + file_info.get("file_size", 0)
        else:
            task["failed_uploads"] = task.get("failed_uploads", 0) + 1

        self._save_task_to_json(task_id, task)
    
    def get_next_pending_task(self) -> Optional[str]:
        """
        获取下一个待处理任务
        
        Returns:
            Optional[str]: 任务ID，如果没有则返回None
        """
        # 基于文件系统：若可用并发槽存在，则返回任意一个 pending 任务ID
        if self._count_active_from_fs() >= self._max_concurrent_tasks:
            return None
        for p in sorted(self._temp_dir.glob("*.json")):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if obj.get("status") in {TaskStatus.PENDING.value, TaskStatus.CREATED.value}:
                return obj.get("task_id")
        return None
    
    def start_task(self, task_id: str) -> bool:
        """
        启动任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功启动
        """
        if not self._check_task_exists_in_filesystem(task_id):
            return False
        if self._count_active_from_fs() >= self._max_concurrent_tasks:
            return False
        task = self._load_task_from_json(task_id)
        if task.get("status") not in {TaskStatus.CREATED.value, TaskStatus.PENDING.value}:
            return False
        task["status"] = TaskStatus.ACTIVE.value
        task["started_at"] = datetime.now()
        task["updated_at"] = datetime.now()
        self._save_task_to_json(task_id, task)
        return True
    
    def complete_task(self, task_id: str, success: bool = True, error_message: Optional[str] = None) -> None:
        """
        完成任务
        
        Args:
            task_id: 任务ID
            success: 是否成功
            error_message: 错误信息
        """
        if not self._check_task_exists_in_filesystem(task_id):
            return
        task = self._load_task_from_json(task_id)
        task["status"] = TaskStatus.COMPLETED.value if success else TaskStatus.FAILED.value
        task["completed_at"] = datetime.now()
        task["updated_at"] = datetime.now()
        if error_message:
            task["error_message"] = error_message

        # 按新策略：不在完成时删除上传原文件，保留结果 JSON
        self._save_task_to_json(task_id, task)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        if not self._check_task_exists_in_filesystem(task_id):
            return False
        task = self._load_task_from_json(task_id)
        if task.get("status") in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
            return False
        task["status"] = TaskStatus.CANCELLED.value
        task["updated_at"] = datetime.now()
        self._save_task_to_json(task_id, task)
        return True
    
    def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 100) -> List[Dict]:
        """
        列出任务
        
        Args:
            status: 可选的状态过滤
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 任务列表
        """
        tasks: List[Dict] = []
        for p in self._temp_dir.glob("*.json"):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if status is None or obj.get("status") == status.value:
                tasks.append(obj)
        # 按 created_at 排序
        def _created_at(o: Dict):
            v = o.get("created_at")
            if isinstance(v, str):
                return v
            return ""
        tasks.sort(key=_created_at, reverse=True)
        return tasks[:limit]
    
    def get_queue_status(self) -> Dict:
        """
        获取队列状态
        
        Returns:
            Dict: 队列状态信息
        """
        pending = 0
        active = 0
        completed = 0
        total = 0
        for p in self._temp_dir.glob("*.json"):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            total += 1
            s = obj.get("status")
            if s == TaskStatus.PENDING.value or s == TaskStatus.CREATED.value:
                pending += 1
            elif s == TaskStatus.ACTIVE.value or s == TaskStatus.PROCESSING.value:
                active += 1
            elif s == TaskStatus.COMPLETED.value:
                completed += 1
        return {
            "pending_count": pending,
            "active_count": active,
            "completed_count": completed,
            "max_concurrent": self._max_concurrent_tasks,
            "total_tasks": total,
        }
    
    def cleanup_expired_tasks(self) -> int:
        """
        无需定期清理任务文件。按需返回 0。
        （根据当前需求：任务完成后仅删除上传的原文件，保留结果 JSON。）
        """
        return 0

    def cleanup_uploaded_sources(self, older_than_days: int = 7) -> Dict[str, int]:
        """
        每周（或指定天数）扫描一次：对已完成且完成时间早于指定天数的任务，
        删除上传的源文件，但不删除任务结果的 JSON 文件。

        Args:
            older_than_days: 判定为“过期”上传源文件的天数阈值（默认7天）

        Returns:
            {"tasks_scanned": x, "tasks_matched": y, "files_deleted": z}
        """
        tasks_scanned = 0
        tasks_matched = 0
        files_deleted = 0

        cutoff = datetime.now() - timedelta(days=older_than_days)
        for p in self._temp_dir.glob("*.json"):
            tasks_scanned += 1
            try:
                obj = self._load_task_from_json(p.stem)
            except Exception:
                continue

            if obj.get("status") != TaskStatus.COMPLETED.value:
                continue

            completed_at = obj.get("completed_at")
            try:
                completed_dt = datetime.fromisoformat(completed_at) if completed_at else None
            except Exception:
                completed_dt = None

            if completed_dt and completed_dt < cutoff:
                tasks_matched += 1
                files = obj.get("files", []) or []
                for info in files:
                    try:
                        file_path = info.get("file_path") if isinstance(info, dict) else None
                        if not file_path:
                            continue
                        fp = Path(file_path)
                        if fp.exists() and fp.is_file():
                            fp.unlink()
                            files_deleted += 1
                    except Exception:
                        pass

        return {"tasks_scanned": tasks_scanned, "tasks_matched": tasks_matched, "files_deleted": files_deleted}
    
    # TODO: 数据库相关方法（预留接口）
    """
    def _save_task_to_db(self, task_info: Dict) -> None:
        # 保存任务到数据库
        pass
    
    def _update_task_in_db(self, task_id: str, task_info: Dict) -> None:
        # 更新数据库中的任务
        pass
    
    def _load_tasks_from_db(self) -> None:
        # 从数据库加载任务
        pass
    
    def _delete_task_from_db(self, task_id: str) -> None:
        # 从数据库删除任务
        pass
    
    def _load_task_from_filesystem(self, task_id: str) -> Dict:
        # 从文件系统加载任务信息
        pass
    """


# 全局任务管理器实例
task_manager = TaskManager()


def validate_or_create_task(task_id: Optional[str] = None, priority: TaskPriority = TaskPriority.NORMAL, 
                          metadata: Optional[Dict] = None) -> str:
    """
    验证或创建任务ID
    
    Args:
        task_id: 可选的任务ID
        priority: 任务优先级
        metadata: 任务元数据
        
    Returns:
        str: 有效的任务ID
    """
    # 处理空字符串和None的情况
    if task_id is None or task_id.strip() == '':
        return task_manager.create_task(priority=priority, metadata=metadata)
    
    # 验证任务ID是否存在且有效
    if not task_manager.validate_task(task_id):
        raise HTTPException(
            status_code=400,
            detail=f"无效的任务ID: {task_id}"
        )
    
    return task_id


def get_task_info(task_id: str) -> Dict:
    """
    获取任务信息
    
    Args:
        task_id: 任务ID
        
    Returns:
        Dict: 任务信息
    """
    return task_manager.get_task(task_id)


def update_task_status(task_id: str, status: TaskStatus, **kwargs) -> None:
    """
    更新任务状态
    
    Args:
        task_id: 任务ID
        status: 新状态
        **kwargs: 其他更新字段
    """
    task_manager.update_task_status(task_id, status, **kwargs)


def add_file_to_task(task_id: str, file_info: Dict) -> None:
    """
    向任务添加文件
    
    Args:
        task_id: 任务ID
        file_info: 文件信息
    """
    task_manager.add_file_to_task(task_id, file_info)


def get_queue_status() -> Dict:
    """
    获取队列状态
    
    Returns:
        Dict: 队列状态
    """
    return task_manager.get_queue_status() 