"""
作业管理器：根据任务入参分发到对应功能模块（占位实现）

说明：
- start_job(task_id) 在任务启动时被调用
- 从 TaskManager 读取任务 JSON，解析 request 配置
- 根据 purpose/target_format 等分发到不同处理分支（当前以 TODO 占位）
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple

from config.logging_config import get_logger
from app.core.task_manager import task_manager as tm, TaskStatus
from config.settings import settings
from pathlib import Path
import traceback

# Converters / Readers
from app.vectorization.chunking import chunk_text
from app.ai.client import AIClient
from app.core.file_manager import FileManager


class JobManager:
    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def start_job(self, task_id: str) -> None:
        """启动任务：顺序化执行（格式转换 -> 内容读取 -> 切块 -> 总结/输出）。"""
        try:
            task_doc = tm.get_task(task_id)
        except Exception as e:
            self.logger.error("start_job: load task failed: %s", e)
            return

        request: Dict[str, Any] = task_doc.get("request") or {}
        purpose = self._get_value(request.get("purpose"))
        target_format = self._get_value(request.get("target_format"))

        self.logger.info("start_job: task_id=%s purpose=%s target_format=%s", task_id, purpose, target_format)

        # 标记处理开始
        try:
            tm.update_task_status(task_id, TaskStatus.PROCESSING)
        except Exception:
            pass

        try:
            files: List[Dict[str, Any]] = (task_doc.get("files") or [])
            if not files:
                self._fail(task_id, "No files associated with this task")
                return

            # 1) 预转换（委托 FileManager 处理 ofd/wps/doc 等）
            pre_converted_files: List[Dict[str, Any]] = []
            for f in files:
                src = f.get("file_path") or ""
                if not src:
                    continue
                fm = FileManager(src)
                new_path = fm.convert_if_needed()
                pre_converted_files.append({**f, "file_path": new_path})

            # 2) 业务上的格式转换（当 purpose=format_conversion 时，委托 FileManager.convert_to_target 落盘）
            converted_files: List[Dict[str, Any]] = pre_converted_files
            if purpose in {"format_conversion"}:
                converted_files = self._handle_format_conversion(task_id, request, pre_converted_files)

            # 3) 内容读取（委托 FileManager.read_text）
            texts: List[Tuple[str, str]] = self._handle_content_reading(task_id, request, converted_files)
            # texts: List[(file_path, text)]

            # 4) 切块（可选）
            enable_chunking = bool(request.get("enable_chunking", False))
            chunks_result: Optional[Dict[str, Any]] = None
            if enable_chunking or (self._get_value(request.get("target_format")) == "chunks"):
                chunks_result = self._handle_chunking(task_id, request, texts)

            # 5) 总结（当目标是 summary 或显式开启多文件总结）
            is_summary_target = (target_format == "summary")
            enable_multi_file_summary = bool(request.get("enable_multi_file_summary", False))
            summary_data: Optional[Dict[str, Any]] = None
            if is_summary_target or enable_multi_file_summary:
                summary_data = self._handle_summary(task_id, request, texts, chunks_result)

            # 6) 输出结果：根据 target_format 优先
            result_payload: Dict[str, Any] = {"url": None, "data": None}
            if target_format == "chunks":
                result_payload["data"] = chunks_result or {"chunks": []}
            elif target_format == "summary":
                result_payload["data"] = summary_data or {"summary": ""}
            elif target_format in {"markdown", "text", "json", "csv", "excel", "dataframe"}:
                # 如果之前做了格式转换，会在 _handle_format_conversion 中写入静态目录
                # 这里仅将路径透出为 url（本地路径占位）
                out_dir = Path(settings.STATIC_DIR) / "converted" / task_id
                if out_dir.exists():
                    result_payload["url"] = str(out_dir.as_posix())
                else:
                    # 回退：直接返回聚合文本
                    joined_text = "\n\n".join([t for _, t in texts])
                    result_payload["data"] = {"text": joined_text}
            else:
                # 默认返回读取的纯文本
                joined_text = "\n\n".join([t for _, t in texts])
                result_payload["data"] = {"text": joined_text}

            tm.update_section(task_id, "process_json", {"result": result_payload})
            tm.update_task_status(task_id, TaskStatus.COMPLETED)
        except Exception:
            self._fail(task_id, f"Unhandled error: {traceback.format_exc()}")
            return

    # ---------------- 占位处理函数（仅 TODO） ----------------
    def _handle_format_conversion(self, task_id: str, request: Dict[str, Any], files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """委托 FileManager.convert_to_target 进行业务转换并落盘到 static 目录。"""
        target_format = self._get_value(request.get("target_format")) or "markdown"
        updated_files: List[Dict[str, Any]] = []
        for f in files:
            src = f.get("file_path") or ""
            if not src:
                continue
            fm = FileManager(src)
            new_path = fm.convert_to_target(target_format, task_id=task_id)
            updated_files.append({**f, "file_path": new_path})
        tm.update_section(task_id, "process_json", {"converted_target_format": target_format})
        return updated_files or files

    def _handle_content_reading(self, task_id: str, request: Dict[str, Any], files: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
        """委托 FileManager.read_text，按目标输出格式分派（markdown/plain_text）。"""
        table_precision = None
        if isinstance(request.get("table_precision"), dict):
            raw_val = request.get("table_precision", {}).get("value")
            if raw_val is not None:
                try:
                    table_precision = int(raw_val)
                except Exception:
                    table_precision = None
        else:
            tp_val = request.get("table_precision")
            if isinstance(tp_val, (int)):
                table_precision = int(tp_val)

        # 使用 target_format 决定阅读输出：markdown or plain text
        target_format = self._get_value(request.get("target_format")) or "text"

        collected: List[Tuple[str, str]] = []
        for f in files:
            fp = f.get("file_path") or ""
            if not fp:
                continue
            fm = FileManager(fp)
            text = fm.read_text(target_format=target_format, table_precision=table_precision)
            collected.append((fp, text))

        tm.update_section(task_id, "process_json", {"read_files": len(collected)})
        return collected

    def _handle_chunking(self, task_id: str, request: Dict[str, Any], texts: List[Tuple[str, str]]) -> Dict[str, Any]:
        """根据请求参数执行切块：返回整体合并结果与逐文件结果。"""
        enable_chunking = bool(request.get("enable_chunking", False))
        strat_value = self._get_value(request.get("chunking_strategy")) or "auto"
        chunk_size = int(request.get("chunk_size", settings.DEFAULT_CHUNK_SIZE) or settings.DEFAULT_CHUNK_SIZE)
        chunk_overlap = int(request.get("chunk_overlap", settings.DEFAULT_CHUNK_OVERLAP) or settings.DEFAULT_CHUNK_OVERLAP)
        chunking_config = request.get("chunking_config") or {}

        client = AIClient()

        # 合并文本进行一次整体切块
        full_text = "\n\n".join([t for _, t in texts])
        merged_result = chunk_text(
            text=full_text,
            enable_chunking=enable_chunking,
            chunking_strategy_value=strat_value,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunking_config=chunking_config,
            ai_client=client,
        )

        # 逐文件切块，便于定位来源
        per_file_results: List[Dict[str, Any]] = []
        for file_path, text in texts:
            r = chunk_text(
                text=text,
                enable_chunking=enable_chunking,
                chunking_strategy_value=strat_value,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                chunking_config=chunking_config,
                ai_client=client,
            )
            per_file_results.append({
                "file_path": file_path,
                "count": len(r.get("chunks", [])),
                "chunks": r.get("chunks", []),
                "derivatives": r.get("derivatives", []),
            })

        result: Dict[str, Any] = {
            "chunks": merged_result.get("chunks", []),
            "derivatives": merged_result.get("derivatives", []),
            "per_file": per_file_results,
        }

        tm.update_section(task_id, "process_json", {
            "chunks_meta": {
                "merged_count": len(result.get("chunks", [])),
                "per_file": [{"file_path": x["file_path"], "count": x["count"]} for x in per_file_results],
            }
        })
        return result

    def _handle_summary(
        self,
        task_id: str,
        request: Dict[str, Any],
        texts: List[Tuple[str, str]],
        chunks_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成摘要（非流式）：使用统一客户端生成要点式摘要。"""
        summary_length = int(request.get("summary_length", 500) or 500)
        summary_focus: List[str] = request.get("summary_focus", ["main_points", "key_findings"]) or []

        content = "\n\n".join([t for _, t in texts])
        if chunks_result and chunks_result.get("chunks"):
            content = "\n\n".join(chunks_result["chunks"])[: 20000]

        client = AIClient()
        focus_str = ", ".join(summary_focus)
        prompt = (
            f"请将以下内容进行总结，长度不超过 {summary_length} 字。重点关注: {focus_str}\n"
            "用中文要点式输出。\n\n" + content
        )
        summary_text = client.chat_invoke(
            messages=[
                {"role": "system", "content": "你是专业的文本总结助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        tm.update_section(task_id, "process_json", {"summary_meta": {"length": len(summary_text)}})
        return {"summary": summary_text}

    # ---------------- 工具 ----------------
    @staticmethod
    def _get_value(v: Optional[Any]) -> Optional[str]:
        if isinstance(v, dict):
            return v.get("value")
        if isinstance(v, str):
            return v
        return None

    def _fail(self, task_id: str, message: str) -> None:
        self.logger.error("task %s failed: %s", task_id, message)
        try:
            tm.update_task_status(task_id, TaskStatus.FAILED, errors={"message": message})
        except Exception:
            pass


# 单例
job_manager = JobManager()


def start_job(task_id: str) -> None:
    job_manager.start_job(task_id)


