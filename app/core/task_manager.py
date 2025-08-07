"""
任务管理器
Task Manager for managing task IDs, states and queues
"""

import uuid
import time
import os
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from enum import Enum
from fastapi import HTTPException
import threading
from queue import Queue, PriorityQueue
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
        # 内存中的任务存储（临时，后续会迁移到数据库）
        self._tasks: Dict[str, Dict] = {}
        self._task_locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        
        # 任务队列管理
        self._pending_queue = PriorityQueue()
        self._active_tasks: Dict[str, Dict] = {}
        self._completed_tasks: Dict[str, Dict] = {}
        
        # 配置
        self._max_concurrent_tasks = 10
        self._task_timeout = 3600  # 1小时超时
        self._cleanup_interval = 300  # 5分钟清理一次
        self._last_cleanup = time.time()
        self._uploads_dir = "uploads"  # 上传目录
        
        # 数据库预留接口（注释形式）
        # self._db_connection = None  # 数据库连接
        # self._db_table_name = "tasks"  # 任务表名
    
    def _check_task_exists_in_filesystem(self, task_id: str) -> bool:
        """
        检查任务在文件系统中是否存在
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 任务是否存在
        """
        task_dir = Path(self._uploads_dir) / task_id
        return task_dir.exists() and task_dir.is_dir()
    
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
        with self._global_lock:
            if task_id is None:
                task_id = str(uuid.uuid4())
            
            # 检查任务ID是否已存在（在内存中或文件系统中）
            if task_id in self._tasks or self._check_task_exists_in_filesystem(task_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"任务ID已存在: {task_id}"
                )
            
            # 创建新任务
            task_info = {
                "task_id": task_id,
                "status": TaskStatus.CREATED.value,
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
                "max_retries": 3
            }
            
            self._tasks[task_id] = task_info
            self._task_locks[task_id] = threading.Lock()
            
            # 添加到待处理队列
            self._pending_queue.put((priority.value, time.time(), task_id))
            
            # TODO: 保存到数据库
            # self._save_task_to_db(task_info)
            
            return task_id
    
    def validate_task(self, task_id: str) -> bool:
        """
        验证任务ID是否存在且有效
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 任务是否存在且有效
        """
        # 首先检查内存中的任务
        with self._global_lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                # 检查任务是否已过期
                if task["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                    return False
                
                # 检查任务是否超时
                if task["started_at"] and (datetime.now() - task["started_at"]).total_seconds() > self._task_timeout:
                    return False
                
                return True
        
        # 如果内存中没有，检查文件系统
        if self._check_task_exists_in_filesystem(task_id):
            return True
        
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
        with self._global_lock:
            if task_id not in self._tasks:
                # 如果内存中没有，尝试从文件系统加载
                if self._check_task_exists_in_filesystem(task_id):
                    # TODO: 从文件系统或数据库加载任务信息
                    # task_info = self._load_task_from_filesystem(task_id)
                    # self._tasks[task_id] = task_info
                    # return task_info.copy()
                    raise HTTPException(
                        status_code=404,
                        detail=f"任务存在但信息不完整: {task_id}"
                    )
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"任务不存在: {task_id}"
                    )
            
            return self._tasks[task_id].copy()
    
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
        
        with self._global_lock:
            if task_id not in self._tasks:
                # 如果内存中没有，尝试从文件系统加载
                if self._check_task_exists_in_filesystem(task_id):
                    # TODO: 从文件系统或数据库加载任务信息
                    # task_info = self._load_task_from_filesystem(task_id)
                    # self._tasks[task_id] = task_info
                    pass
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"任务不存在: {task_id}"
                    )
            
            task = self._tasks[task_id]
            task["status"] = status.value
            task["updated_at"] = datetime.now()
            
            # 根据状态更新相应字段
            if status == TaskStatus.ACTIVE:
                task["started_at"] = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task["completed_at"] = datetime.now()
            
            # 更新其他字段
            task.update(kwargs)
            
            # TODO: 更新数据库
            # self._update_task_in_db(task_id, task)
    
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
        
        with self._task_locks.get(task_id, self._global_lock):
            if task_id not in self._tasks:
                # 如果内存中没有，尝试从文件系统加载
                if self._check_task_exists_in_filesystem(task_id):
                    # TODO: 从文件系统或数据库加载任务信息
                    # task_info = self._load_task_from_filesystem(task_id)
                    # self._tasks[task_id] = task_info
                    pass
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"任务不存在: {task_id}"
                    )
            
            task = self._tasks[task_id]
            task["files"].append(file_info)
            task["file_count"] = len(task["files"])
            task["updated_at"] = datetime.now()
            
            # 更新统计信息
            if file_info.get("status") == "success":
                task["successful_uploads"] += 1
                task["total_size"] += file_info.get("file_size", 0)
            else:
                task["failed_uploads"] += 1
            
            # TODO: 更新数据库
            # self._update_task_in_db(task_id, task)
    
    def get_next_pending_task(self) -> Optional[str]:
        """
        获取下一个待处理任务
        
        Returns:
            Optional[str]: 任务ID，如果没有则返回None
        """
        with self._global_lock:
            if self._pending_queue.empty():
                return None
            
            # 检查是否有可用的处理槽
            if len(self._active_tasks) >= self._max_concurrent_tasks:
                return None
            
            try:
                priority, timestamp, task_id = self._pending_queue.get_nowait()
                
                # 验证任务是否仍然有效
                if task_id in self._tasks and self._tasks[task_id]["status"] == TaskStatus.CREATED.value:
                    return task_id
                else:
                    # 任务已失效，继续获取下一个
                    return self.get_next_pending_task()
                    
            except:
                return None
    
    def start_task(self, task_id: str) -> bool:
        """
        启动任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功启动
        """
        with self._global_lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            if task["status"] != TaskStatus.CREATED.value:
                return False
            
            # 检查是否超过最大并发数
            if len(self._active_tasks) >= self._max_concurrent_tasks:
                return False
            
            # 启动任务
            task["status"] = TaskStatus.ACTIVE.value
            task["started_at"] = datetime.now()
            task["updated_at"] = datetime.now()
            
            self._active_tasks[task_id] = task
            
            # TODO: 更新数据库
            # self._update_task_in_db(task_id, task)
            
            return True
    
    def complete_task(self, task_id: str, success: bool = True, error_message: Optional[str] = None) -> None:
        """
        完成任务
        
        Args:
            task_id: 任务ID
            success: 是否成功
            error_message: 错误信息
        """
        with self._global_lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            task["status"] = TaskStatus.COMPLETED.value if success else TaskStatus.FAILED.value
            task["completed_at"] = datetime.now()
            task["updated_at"] = datetime.now()
            
            if error_message:
                task["error_message"] = error_message
            
            # 从活跃任务中移除
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]
            
            # 添加到已完成任务
            self._completed_tasks[task_id] = task
            
            # TODO: 更新数据库
            # self._update_task_in_db(task_id, task)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        with self._global_lock:
            if task_id not in self._tasks:
                return False
            
            task = self._tasks[task_id]
            if task["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                return False
            
            task["status"] = TaskStatus.CANCELLED.value
            task["updated_at"] = datetime.now()
            
            # 从活跃任务中移除
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]
            
            # TODO: 更新数据库
            # self._update_task_in_db(task_id, task)
            
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
        with self._global_lock:
            tasks = []
            for task_id, task_info in self._tasks.items():
                if status is None or task_info["status"] == status.value:
                    tasks.append(task_info.copy())
            
            # 按创建时间排序
            tasks.sort(key=lambda x: x["created_at"], reverse=True)
            
            return tasks[:limit]
    
    def get_queue_status(self) -> Dict:
        """
        获取队列状态
        
        Returns:
            Dict: 队列状态信息
        """
        with self._global_lock:
            return {
                "pending_count": self._pending_queue.qsize(),
                "active_count": len(self._active_tasks),
                "completed_count": len(self._completed_tasks),
                "max_concurrent": self._max_concurrent_tasks,
                "total_tasks": len(self._tasks)
            }
    
    def cleanup_expired_tasks(self) -> int:
        """
        清理过期的任务
        
        Returns:
            int: 清理的任务数量
        """
        current_time = time.time()
        
        # 检查是否需要清理
        if current_time - self._last_cleanup < self._cleanup_interval:
            return 0
        
        with self._global_lock:
            expired_tasks = []
            cutoff_time = datetime.now() - timedelta(seconds=self._task_timeout)
            
            for task_id, task_info in self._tasks.items():
                # 清理已完成且超过24小时的任务
                if (task_info["status"] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value] and
                    task_info["completed_at"] and 
                    task_info["completed_at"] < cutoff_time):
                    expired_tasks.append(task_id)
            
            # 删除过期任务
            for task_id in expired_tasks:
                del self._tasks[task_id]
                if task_id in self._task_locks:
                    del self._task_locks[task_id]
                if task_id in self._completed_tasks:
                    del self._completed_tasks[task_id]
            
            self._last_cleanup = current_time
            return len(expired_tasks)
    
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