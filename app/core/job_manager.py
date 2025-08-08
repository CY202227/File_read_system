"""
作业管理器：根据任务入参分发到对应功能模块（占位实现）

说明：
- start_job(task_id) 在任务启动时被调用
- 从 TaskManager 读取任务 JSON，解析 request 配置
- 根据 purpose/target_format 等分发到不同处理分支（当前以 TODO 占位）
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from config.logging_config import get_logger
from app.core.task_manager import task_manager as tm


class JobManager:
    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def start_job(self, task_id: str) -> None:
        """启动任务：读取参数并分发到对应模块（占位）。"""
        try:
            task_doc = tm.get_task(task_id)
        except Exception as e:
            self.logger.error("start_job: load task failed: %s", e)
            return

        request: Dict[str, Any] = task_doc.get("request") or {}
        purpose = self._get_value(request.get("purpose"))
        target_format = self._get_value(request.get("target_format"))

        self.logger.info("start_job: task_id=%s purpose=%s target_format=%s", task_id, purpose, target_format)

        # TODO: 将任务状态置为 processing / active 的细化由 TaskManager/调度器处理

        # 分发逻辑（占位）：
        if purpose == "format_conversion":
            self._handle_format_conversion(task_id, request)
        elif purpose == "content_reading":
            if target_format == "summary":
                self._handle_summary(task_id, request)
            elif target_format == "chunks":
                self._handle_chunking(task_id, request)
            else:
                self._handle_content_reading(task_id, request)
        elif purpose == "both":
            # 先读取，再按目标格式处理
            self._handle_content_reading(task_id, request)
            if target_format == "summary":
                self._handle_summary(task_id, request)
            elif target_format == "chunks":
                self._handle_chunking(task_id, request)
            else:
                self._handle_format_conversion(task_id, request)
        else:
            self.logger.warning("start_job: unknown purpose=%s", purpose)

    # ---------------- 占位处理函数（仅 TODO） ----------------
    def _handle_format_conversion(self, task_id: str, request: Dict[str, Any]) -> None:
        self.logger.info("[TODO] format_conversion: task_id=%s", task_id)
        # TODO: 解析源文件，转换为 target_format（markdown/json/csv/excel/...）并写入 result.url 或 result.data

    def _handle_content_reading(self, task_id: str, request: Dict[str, Any]) -> None:
        self.logger.info("[TODO] content_reading: task_id=%s", task_id)
        # TODO: 读取文本/表格内容，根据 content_return_format 结构化输出

    def _handle_chunking(self, task_id: str, request: Dict[str, Any]) -> None:
        self.logger.info("[TODO] chunking: task_id=%s", task_id)
        # TODO: 根据 chunking_strategy/size/overlap 进行切块，生成 chunks 输出

    def _handle_summary(self, task_id: str, request: Dict[str, Any]) -> None:
        self.logger.info("[TODO] summary: task_id=%s", task_id)
        # TODO: 如 summary_streaming=true，通过事件通道增量推送；否则直接生成完成后写 result

    # ---------------- 工具 ----------------
    @staticmethod
    def _get_value(v: Optional[Any]) -> Optional[str]:
        if isinstance(v, dict):
            return v.get("value")
        if isinstance(v, str):
            return v
        return None


# 单例
job_manager = JobManager()


def start_job(task_id: str) -> None:
    job_manager.start_job(task_id)


