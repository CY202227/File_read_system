"""
作业管理器：根据任务入参分发到对应功能模块（占位实现）

说明：
- start_job(task_id) 在任务启动时被调用
- 从 TaskManager 读取任务 JSON，解析 request 配置
- 根据 target_format 等分发到不同处理分支
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Tuple
import asyncio
import functools
import inspect

from config.logging_config import get_logger
from app.core.task_manager import task_manager as tm, TaskStatus
from config.settings import settings
from config.constants import CONTENT_READING_OUTPUT_FORMATS
 
import traceback

# Converters / Readers
from app.vectorization.chunking import chunk_text
from app.ai.client import AIClient
from app.core.file_manager import FileManager
from app.processors.information_extraction import extract_information


def _build_log_message(func, bound: inspect.BoundArguments) -> str:
    parts: List[str] = []
    for key in ["task_id", "target_format", "purpose", "file_path"]:
        if key in bound.arguments:
            val = bound.arguments.get(key)
            try:
                parts.append(f"{key}={val}")
            except Exception:
                parts.append(f"{key}=?")
    return ", ".join(parts)


def log_call(func):
    sig = inspect.signature(func)
    is_coro = asyncio.iscoroutinefunction(func)

    @functools.wraps(func)
    async def _aw(*args, **kwargs):
        logger = get_logger(func.__module__)
        try:
            bound = sig.bind_partial(*args, **kwargs)
        except Exception:
            bound = inspect.Signature().bind_partial()
        logger.info("enter %s(%s)", func.__qualname__, _build_log_message(func, bound))
        return await func(*args, **kwargs)

    @functools.wraps(func)
    def _sw(*args, **kwargs):
        logger = get_logger(func.__module__)
        try:
            bound = sig.bind_partial(*args, **kwargs)
        except Exception:
            bound = inspect.Signature().bind_partial()
        logger.info("enter %s(%s)", func.__qualname__, _build_log_message(func, bound))
        return func(*args, **kwargs)

    return _aw if is_coro else _sw


class JobManager:
    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    @log_call
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
        supported_formats = CONTENT_READING_OUTPUT_FORMATS
        if target_format not in supported_formats:
            target_format = "plain_text"

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

            # 2) 直接使用预转换后的文件列表
            converted_files: List[Dict[str, Any]] = pre_converted_files

            # 3) 内容读取（委托 FileManager.read_text）
            texts: List[Tuple[str, Any]] = self._handle_content_reading(task_id, request, converted_files)
            # texts: List[(file_path, text)]

            # 4) 切块（可选）
            enable_chunking = bool(request.get("enable_chunking", False))
            chunks_result: Optional[Dict[str, Any]] = None
            if enable_chunking or (self._get_value(request.get("target_format")) == "chunks"):
                chunks_result = self._handle_chunking(task_id, request, texts)

            # 5) 信息抽取（仅当 enable_extract 为 True）
            extraction_result: Optional[Dict[str, Any]] = None
            try:
                enable_extract = bool(request.get("enable_extract", False))
                if enable_extract:
                    cfg = request.get("extract_config") or {}
                    merged_text = "\n\n".join([t for _, t in texts if isinstance(t, str)])
                    if merged_text.strip():
                        extraction_result = extract_information(merged_text, cfg)
            except Exception as e:
                self.logger.warning("information_extraction skipped or failed: %s", e)
                extraction_result = None

            # 6) 总结（当目标是 summary 或显式开启多文件总结）
            is_summary_target = (target_format == "summary")
            enable_multi_file_summary = bool(request.get("enable_multi_file_summary", False))
            summary_data: Optional[Dict[str, Any]] = None
            if is_summary_target or enable_multi_file_summary:
                summary_data = self._handle_summary(task_id, request, texts, chunks_result)

            # 7) 输出结果：统一返回内存数据
            data_dict: Dict[str, Any] = {}
            if target_format == "chunks":
                data_dict.update(chunks_result or {"chunks": []})
            elif target_format == "summary":
                data_dict.update(summary_data or {"summary": ""})
            elif target_format == "dataframe":
                non_string_payloads = [t for _, t in texts if not isinstance(t, str)]
                if len(non_string_payloads) == 1:
                    data_dict["records"] = non_string_payloads[0]
                else:
                    data_dict["records_list"] = non_string_payloads
            elif target_format in {"markdown", "plain_text"}:
                joined_text = "\n\n".join([t for _, t in texts if isinstance(t, str)])
                data_dict["text"] = joined_text
            else:
                joined_text = "\n\n".join([t for _, t in texts if isinstance(t, str)])
                data_dict["text"] = joined_text

            # 附加：无论目标为何，只要有切块/摘要/抽取，均在 result_data 下附带
            if chunks_result is not None:
                data_dict["chunking"] = chunks_result
            if summary_data is not None:
                data_dict["summary"] = summary_data
            if extraction_result is not None:
                data_dict["extraction"] = extraction_result

            result_payload: Dict[str, Any] = {"url": None, "data": data_dict}

            # 将结果同时写入分段与顶层，保证查询与直返一致
            tm.update_section(task_id, "process_json", {"result": result_payload})
            tm.update_task_status(task_id, TaskStatus.COMPLETED, result=result_payload)
        except Exception:
            self._fail(task_id, f"Unhandled error: {traceback.format_exc()}")
            return

    # ---------------- 占位处理函数（仅 TODO） ----------------
    @log_call
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

    @log_call
    def _handle_content_reading(self, task_id: str, request: Dict[str, Any], files: List[Dict[str, Any]]) -> List[Tuple[str, Any]]:
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

        # 使用 target_format 决定阅读输出：markdown / plain_text / dataframe
        target_format = self._get_value(request.get("target_format")) or "plain_text"
        if target_format == "text":
            target_format = "plain_text"

        collected: List[Tuple[str, Any]] = []
        for f in files:
            fp = f.get("file_path") or ""
            if not fp:
                continue
            fm = FileManager(fp)
            try:
                text = fm.read_text(target_format=target_format, table_precision=table_precision)
                collected.append((fp, text))
            except Exception as e:
                # dataframe 仅支持表格类文件：对不支持的类型容错跳过
                if target_format == "dataframe":
                    self.logger.warning("skip non-tabular file for dataframe target: %s (%s)", fp, e)
                    continue
                raise

        tm.update_section(task_id, "process_json", {"read_files": len(collected)})
        return collected

    @log_call
    def _handle_chunking(self, task_id: str, request: Dict[str, Any], texts: List[Tuple[str, Any]]) -> Dict[str, Any]:
        """根据请求参数执行切块：返回整体合并结果与逐文件结果。"""
        enable_chunking = bool(request.get("enable_chunking", False))
        strat_value = self._get_value(request.get("chunking_strategy")) or "auto"
        chunk_size = int(request.get("chunk_size", settings.DEFAULT_CHUNK_SIZE) or settings.DEFAULT_CHUNK_SIZE)
        chunk_overlap = int(request.get("chunk_overlap", settings.DEFAULT_CHUNK_OVERLAP) or settings.DEFAULT_CHUNK_OVERLAP)
        chunking_config = request.get("chunking_config") or {}

        # 若未启用切块，直接返回原文作为单块，避免无意义调用
        if not enable_chunking:
            full_text = "\n\n".join([t for _, t in texts if isinstance(t, str)])
            return {"chunks": [full_text], "derivatives": [], "per_file": []}

        client = AIClient()

        # 合并文本进行一次整体切块
        full_text = "\n\n".join([t for _, t in texts if isinstance(t, str)])
        merged_result = chunk_text(
            text=full_text,
            enable_chunking=True,
            chunking_strategy_value=strat_value,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunking_config=chunking_config,
            ai_client=client,
        )

        # 逐文件切块，便于定位来源
        per_file_results: List[Dict[str, Any]] = []
        for file_path, text in texts:
            # 跳过非字符串内容（例如 dataframe 目标下的结构化数据）
            if not isinstance(text, str):
                continue
            r = chunk_text(
                text=text,
                enable_chunking=True,
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

    @log_call
    def _handle_summary(
        self,
        task_id: str,
        request: Dict[str, Any],
        texts: List[Tuple[str, Any]],
        chunks_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成摘要（非流式）：使用统一客户端生成要点式摘要。"""
        summary_length = int(request.get("summary_length", 500) or 500)
        summary_focus: List[str] = request.get("summary_focus", ["main_points", "key_findings"]) or []
        # 可选：仅返回前 K 条要点
        k: Optional[int] = None
        try:
            raw_k = request.get("summary_return_top_k")
            if isinstance(raw_k, dict):
                raw_k = raw_k.get("value")
            if raw_k is not None:
                k = int(raw_k)
                if k <= 0:
                    k = None
        except Exception:
            k = None

        content = "\n\n".join([t for _, t in texts if isinstance(t, str)])
        if chunks_result and chunks_result.get("chunks"):
            content = "\n\n".join(chunks_result["chunks"])[: 20000]
        # 若无可用内容，则直接返回空摘要，避免模型生成模板化内容
        if not (content or "").strip():
            tm.update_section(task_id, "process_json", {"summary_meta": {"length": 0, "empty": True}})
            return {"summary": "", "summary_dict": {}}

        client = AIClient()
        focus_str = ", ".join(summary_focus)
        extra_topk_hint = f"请尽量输出不超过 {k} 条要点，每行一条。\n" if k else ""
        prompt = (
            extra_topk_hint
            + f"请将以下内容进行总结，长度不超过 {summary_length} 字。重点关注: {focus_str}\n"
            + "用中文要点式输出。\n\n" + content
        )
        summary_text = client.chat_invoke(
            messages=[
                {"role": "system", "content": "你是专业的文本总结助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2
        )
        # 事后裁剪前 K 条要点（健壮解析）
        if k is not None:
            summary_text = self._take_top_k_points(summary_text, k)

        points_list = self._extract_points(summary_text)
        if k is not None and points_list:
            points_list = points_list[:k]
        summary_dict = {f"p{i+1}": p for i, p in enumerate(points_list)}

        meta: Dict[str, Any] = {"length": len(summary_text), "paragraphs": len(points_list)}
        if k is not None:
            meta["top_k"] = k
        tm.update_section(task_id, "process_json", {"summary_meta": meta})
        return {"summary": summary_text, "summary_dict": summary_dict}

    @staticmethod
    def _take_top_k_points(text: str, k: int) -> str:
        """从模型输出中抽取前 k 条要点，尽量稳健。

        优先解析 JSON 数组；否则按常见要点符号/编号匹配；再否则按段落切分。
        """
        if k <= 0:
            return text
        import re
        import json
        # 尝试 JSON 数组
        try:
            m = re.search(r"\[\s*[\s\S]*?\]", text)
            if m:
                arr = json.loads(m.group(0))
                if isinstance(arr, list) and arr:
                    items = [str(x).strip() for x in arr if isinstance(x, (str, int, float))]
                    if items:
                        items = items[:k]
                        return "\n".join(f"- {it}" for it in items if it)
        except Exception:
            pass
        # 匹配要点行
        bullets: List[str] = []
        bullet_re = re.compile(r"^\s*(?:[-*•·]|\d+[.)、])\s+(.*\S)\s*$")
        for line in text.splitlines():
            m = bullet_re.match(line)
            if m:
                bullets.append(m.group(1).strip())
            if len(bullets) >= k:
                break
        if bullets:
            return "\n".join(f"- {it}" for it in bullets[:k] if it)
        # 退化为段落切分
        paras = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        return "\n".join(f"- {p}" for p in paras[:k])

    @staticmethod
    def _extract_points(text: str) -> List[str]:
        """从文本中提取要点列表：优先识别项目符号，否则按段落。

        返回清洗过的字符串列表。
        """
        import re
        import json
        # JSON 数组
        try:
            m = re.search(r"\[\s*[\s\S]*?\]", text)
            if m:
                arr = json.loads(m.group(0))
                if isinstance(arr, list) and arr:
                    items = [str(x).strip() for x in arr if isinstance(x, (str, int, float))]
                    return [it for it in items if it]
        except Exception:
            pass
        # 项目符号
        bullet_re = re.compile(r"^\s*(?:[-*•·]|\d+[.)、])\s+(.*\S)\s*$")
        bullets: List[str] = []
        for line in text.splitlines():
            m = bullet_re.match(line)
            if m:
                bullets.append(m.group(1).strip())
        if bullets:
            return bullets
        # 段落
        paras = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        return paras

    # ---------------- 工具 ----------------
    @staticmethod
    @log_call
    def _get_value(v: Optional[Any]) -> Optional[str]:
        if isinstance(v, dict):
            return v.get("value")
        if isinstance(v, str):
            return v
        return None

    @log_call
    def _fail(self, task_id: str, message: str) -> None:
        self.logger.error("task %s failed: %s", task_id, message)
        try:
            tm.update_task_status(task_id, TaskStatus.FAILED, errors={"message": message})
        except Exception:
            pass


# 单例
job_manager = JobManager()


@log_call
def start_job(task_id: str) -> None:
    job_manager.start_job(task_id)


