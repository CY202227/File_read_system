"""
文件阅读系统 MCP 服务器
File Reading System MCP Server

基于 FastMCP 实现的文件处理和上传工具
"""

import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path
import traceback

from fastmcp import FastMCP

from config.logging_config import get_logger
from app.core.task_manager import (
    task_manager,
    validate_or_create_task,
    update_task_status,
    add_file_to_task,
    TaskStatus,
    TaskPriority
)
from app.utils.file_utils import (
    generate_file_uuid,
    copy_local_file,
    get_file_info,
)
from app.utils.text_utils import save_text_content
from app.core.job_manager import start_job
from starlette.concurrency import run_in_threadpool

# 导入请求和响应模型
from app.api.schemas.file_process_schemas import (
    FileProcessRequest,
    FileProcessResponse,
    ProcessingPurpose,
    OutputFormat
)
from app.api.schemas.file_read_schemas import (
    FileReadRequest,
    FileReadResponse
)
from app.api.schemas.file_chunk_schemas import (
    FileChunkResponse
)
from app.api.schemas.file_summarize_schemas import (
    FileSummarizeResponse
)
from app.api.schemas.file_extract_schemas import (
    FileExtractResponse
)
from app.api.schemas.upload_schemas import (
    UploadResponse,
    FileUploadInfo,
)

logger = get_logger(__name__)

# 创建 MCP 服务器实例
mcp = FastMCP("文件阅读系统 MCP 服务器")

# 进程内串行队列锁：保证同一进程内按提交顺序依次处理
_queue_lock = asyncio.Lock()


@mcp.tool()
async def upload_files_by_stream(
    file_paths: List[str],
    task_id: Optional[str] = None,
    priority: str = "NORMAL"
) -> str:
    """
    通过文件流上传文件（支持单个或多个文件）

    Args:
        file_paths: 要上传的文件路径列表
        task_id: 可选的任务ID，如果不提供将自动生成
        priority: 任务优先级 (LOW=1, NORMAL=2, HIGH=3, URGENT=4)

    Returns:
        JSON格式的上传结果字符串
    """
    try:
        logger.info(f"upload_files_by_stream: task_id={task_id}, files={len(file_paths)}")

        # 解析优先级
        task_priority = TaskPriority[priority.upper()] if priority else TaskPriority.NORMAL

        # 处理task_id，确保空字符串被转换为None
        if task_id is not None and task_id.strip() == '':
            task_id = None

        # 验证或创建任务ID
        task_id = validate_or_create_task(task_id, priority=task_priority)

        # 更新任务状态为活跃
        update_task_status(task_id, TaskStatus.ACTIVE)

        file_uploads = []
        successful_count = 0
        failed_count = 0

        for file_path in file_paths:
            try:
                file_uuid = generate_file_uuid()

                # 复制文件到任务目录
                dest_path, original_filename = await copy_local_file(
                    source_path=file_path,
                    task_id=task_id,
                    file_uuid=file_uuid
                )

                # 获取文件信息
                file_info = get_file_info(dest_path)

                file_upload_info = FileUploadInfo(
                    file_uuid=file_uuid,
                    original_filename=original_filename,
                    file_path=dest_path,
                    file_size=file_info.get("size", 0),
                    status="success",
                    error_message=None
                )

                file_uploads.append(file_upload_info)
                successful_count += 1

                # 向任务管理器添加文件信息
                add_file_to_task(task_id, {
                    "file_uuid": file_uuid,
                    "original_filename": original_filename,
                    "file_path": dest_path,
                    "file_size": file_info.get("size", 0),
                    "status": "success",
                    "uploaded_at": str(file_info.get("created_time", ""))
                })

            except Exception as e:
                file_upload_info = FileUploadInfo(
                    file_uuid=generate_file_uuid(),
                    original_filename=Path(file_path).name if file_path else "unknown",
                    file_path="",
                    file_size=0,
                    status="error",
                    error_message=str(e)
                )
                file_uploads.append(file_upload_info)
                failed_count += 1

                # 向任务管理器添加失败的文件信息
                add_file_to_task(task_id, {
                    "file_uuid": file_upload_info.file_uuid,
                    "original_filename": file_upload_info.original_filename,
                    "file_path": "",
                    "file_size": 0,
                    "status": "error",
                    "error_message": str(e)
                })

        # 更新任务状态
        final_status = TaskStatus.COMPLETED if failed_count == 0 else TaskStatus.FAILED
        update_task_status(task_id, final_status)

        response = UploadResponse(
            task_id=task_id,
            total_files=len(file_paths),
            successful_uploads=successful_count,
            failed_uploads=failed_count,
            files=file_uploads,
            message=f"文件上传完成，成功: {successful_count}, 失败: {failed_count}"
        )

        return response.model_dump_json(indent=2)

    except Exception as e:
        logger.exception(f"upload_files_by_stream failed: {str(e)}")
        error_detail = f"文件上传失败: {str(e)}"
        if hasattr(e, '__traceback__'):
            error_detail += f"\nTraceback: {traceback.format_exc()}"
        return f'{{"error": "{error_detail}"}}'


@mcp.tool()
async def upload_text_content_tool(
    content: str,
    task_id: Optional[str] = None,
    priority: str = "NORMAL",
    auto_detect: bool = True,
    extension: Optional[str] = None
) -> str:
    """
    上传纯文本内容

    Args:
        content: 纯文本内容
        task_id: 可选的任务ID，如果不提供将自动生成
        priority: 任务优先级 (LOW=1, NORMAL=2, HIGH=3, URGENT=4)
        auto_detect: 是否自动检测文本格式
        extension: 手动模式下的文件扩展名（仅在auto_detect=false时需要）

    Returns:
        JSON格式的上传结果字符串
    """
    try:
        logger.info(f"upload_text_content_tool: task_id={task_id}, content_length={len(content)}")

        # 解析优先级
        task_priority = TaskPriority[priority.upper()] if priority else TaskPriority.NORMAL

        # 处理task_id，确保空字符串被转换为None
        if task_id is not None and task_id.strip() == '':
            task_id = None

        # 验证或创建任务ID
        task_id = validate_or_create_task(task_id, priority=task_priority)

        # 更新任务状态为活跃
        update_task_status(task_id, TaskStatus.ACTIVE)

        # 验证手动模式下的扩展名参数
        if not auto_detect and not extension:
            return '{"error": "手动模式下必须提供文件扩展名"}'

        try:
            file_uuid = generate_file_uuid()

            # 保存文本内容
            file_path, original_filename = await save_text_content(
                content=content,
                task_id=task_id,
                file_uuid=file_uuid,
                auto_detect=auto_detect,
                extension=extension
            )

            # 获取文件信息
            file_info = get_file_info(file_path)

            file_upload_info = FileUploadInfo(
                file_uuid=file_uuid,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_info.get("size", 0),
                status="success",
                error_message=None
            )

            # 向任务管理器添加文件信息
            add_file_to_task(task_id, {
                "file_uuid": file_uuid,
                "original_filename": original_filename,
                "file_path": file_path,
                "file_size": file_info.get("size", 0),
                "status": "success",
                "uploaded_at": str(file_info.get("created_time", ""))
            })

            # 更新任务状态为完成
            update_task_status(task_id, TaskStatus.COMPLETED)

            response = UploadResponse(
                task_id=task_id,
                total_files=1,
                successful_uploads=1,
                failed_uploads=0,
                files=[file_upload_info],
                message=f"文本内容上传成功，文件名: {original_filename}"
            )

            return response.model_dump_json(indent=2)

        except Exception as e:
            file_upload_info = FileUploadInfo(
                file_uuid=generate_file_uuid(),
                original_filename="text_upload",
                file_path="",
                file_size=0,
                status="error",
                error_message=str(e)
            )

            # 向任务管理器添加失败的文件信息
            add_file_to_task(task_id, {
                "file_uuid": file_upload_info.file_uuid,
                "original_filename": file_upload_info.original_filename,
                "file_path": "",
                "file_size": 0,
                "status": "error",
                "error_message": str(e)
            })

            # 更新任务状态为失败
            update_task_status(task_id, TaskStatus.FAILED)

            response = UploadResponse(
                task_id=task_id,
                total_files=1,
                successful_uploads=0,
                failed_uploads=1,
                files=[file_upload_info],
                message=f"文本内容上传失败: {str(e)}"
            )

            return response.model_dump_json(indent=2)

    except Exception as e:
        logger.exception(f"upload_text_content_tool failed: {str(e)}")
        error_detail = f"文本内容上传失败: {str(e)}"
        if hasattr(e, '__traceback__'):
            error_detail += f"\nTraceback: {traceback.format_exc()}"
        return f'{{"error": "{error_detail}"}}'


@mcp.tool()
async def process_file_tool(
    task_id: str,
    purpose: str = "content_reading",
    target_format: str = "plain_text",
    enable_ocr: bool = True
) -> str:
    """
    提交文件处理任务（同步：内部队列顺序执行，完成后直接返回结果）

    Args:
        task_id: 任务ID
        purpose: 处理目的 (content_reading, content_analysis, etc.)
        target_format: 目标格式 (plain_text, markdown, json, etc.)
        enable_ocr: 是否启用OCR

    Returns:
        JSON格式的处理结果字符串
    """
    try:
        logger.info(f"process_file_tool: task_id={task_id}")

        # 构建请求对象
        request = FileProcessRequest(
            task_id=task_id,
            purpose=ProcessingPurpose(value=purpose),
            target_format=OutputFormat(value=target_format),
            enable_ocr=enable_ocr
        )

        # 保存入参到 JSON 并初始化任务
        task_manager.create_task_from_request(
            task_id=request.task_id,
            request_dict=request.model_dump(mode="json"),
        )

        # 内部串行队列：按顺序执行，当前请求阻塞直至完成并返回最终结果
        async with _queue_lock:
            try:
                await run_in_threadpool(start_job, request.task_id)
            except Exception:
                logger.exception(f"start_job failed for task_id={request.task_id}")

        status = task_manager.get_status_from_json(request.task_id)
        return FileProcessResponse(**status).model_dump_json(indent=2)

    except Exception as e:
        logger.exception(f"process_file_tool failed: {str(e)}")
        return f'{{"error": "文件处理失败: {str(e)}"}}'


@mcp.tool()
async def read_file_content_tool(
    task_id: str,
    purpose: str = "content_reading",
    target_format: str = "plain_text",
    enable_ocr: bool = True
) -> str:
    """
    文件内容读取接口（仅执行文件读取步骤）

    Args:
        task_id: 任务ID
        purpose: 处理目的
        target_format: 目标格式
        enable_ocr: 是否启用OCR

    Returns:
        JSON格式的读取结果字符串
    """
    try:
        logger.info(f"read_file_content_tool: task_id={task_id}")

        # 构建请求对象
        request = FileReadRequest(
            task_id=task_id,
            purpose=ProcessingPurpose(value=purpose),
            target_format=OutputFormat(value=target_format),
            enable_ocr=enable_ocr
        )

        # 保存入参到 JSON 并初始化任务
        task_manager.create_task_from_request(
            task_id=request.task_id,
            request_dict=request.model_dump(mode="json"),
        )

        # 内部串行队列：按顺序执行，当前请求阻塞直至完成并返回最终结果
        async with _queue_lock:
            try:
                await run_in_threadpool(start_job, request.task_id)
            except Exception:
                logger.exception(f"start_job failed for task_id={request.task_id}")

        status = task_manager.get_status_from_json(request.task_id)
        return FileReadResponse(**status).model_dump_json(indent=2)

    except Exception as e:
        logger.exception(f"read_file_content_tool failed: {str(e)}")
        return f'{{"error": "文件读取失败: {str(e)}"}}'


@mcp.tool()
async def chunk_file_content_tool(
    task_id: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    chunking_strategy: str = "recursive"
) -> str:
    """
    文件切片接口（执行文件切片步骤，如需会自动调用读取）

    Args:
        task_id: 任务ID
        chunk_size: 切片大小
        chunk_overlap: 切片重叠大小
        chunking_strategy: 切片策略

    Returns:
        JSON格式的切片结果字符串
    """
    try:
        logger.info(f"chunk_file_content_tool: task_id={task_id}")

        # 检查是否已经读取过文件内容
        try:
            # 尝试获取任务状态，如果不存在会抛出异常
            task_manager.get_status_from_json(task_id)
        except Exception:
            # 文件尚未读取，先自动调用读取接口
            logger.info(f"Task {task_id} not found, auto-calling file/read first")
            await read_file_content_tool(
                task_id=task_id,
                purpose="content_reading",
                target_format="plain_text",
                enable_ocr=True
            )

        # 构建包含切片参数的请求
        from app.api.schemas.file_chunk_schemas import ChunkingStrategy, ChunkingConfig
        request_dict = {
            "task_id": task_id,
            "enable_chunking": True,
            "target_format": {"value": "plain_text"},
            "chunking_strategy": ChunkingStrategy(value=chunking_strategy).model_dump(),
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "chunking_config": ChunkingConfig().model_dump()
        }

        # 保存入参到 JSON 并初始化任务
        task_manager.create_task_from_request(
            task_id=task_id,
            request_dict=request_dict,
        )

        # 直接执行任务，不使用队列锁
        try:
            await run_in_threadpool(start_job, task_id)
        except Exception:
            logger.exception(f"start_job failed for task_id={task_id}")

        status = task_manager.get_status_from_json(task_id)

        # 从result_data中提取切片结果
        if status.get("result_data") and status["result_data"].get("chunking"):
            chunking_data = status["result_data"]["chunking"]
            status.update({
                "chunks": chunking_data.get("chunks"),
                "derivatives": chunking_data.get("derivatives"),
                "per_file": chunking_data.get("per_file"),
                "chunks_meta": chunking_data.get("chunks_meta")
            })

        return FileChunkResponse(**status).model_dump_json(indent=2)

    except Exception as e:
        logger.exception(f"chunk_file_content_tool failed: {str(e)}")
        return f'{{"error": "文件切片失败: {str(e)}"}}'


@mcp.tool()
async def summarize_file_content_tool(
    task_id: str,
    summary_length: str = "medium",
    summary_focus: Optional[str] = None,
    summary_return_top_k: Optional[int] = None
) -> str:
    """
    文件总结接口（执行文件总结步骤，如需会自动调用读取）

    Args:
        task_id: 任务ID
        summary_length: 总结长度 (short, medium, long)
        summary_focus: 总结焦点
        summary_return_top_k: 返回前K个结果

    Returns:
        JSON格式的总结结果字符串
    """
    try:
        logger.info(f"summarize_file_content_tool: task_id={task_id}")

        # 检查是否已经读取过文件内容
        try:
            # 尝试获取任务状态，如果不存在会抛出异常
            task_manager.get_status_from_json(task_id)
        except Exception:
            # 文件尚未读取，先自动调用读取接口
            logger.info(f"Task {task_id} not found, auto-calling file/read first")
            await read_file_content_tool(
                task_id=task_id,
                purpose="content_reading",
                target_format="plain_text",
                enable_ocr=True
            )

        # 构建包含总结参数的请求
        request_dict = {
            "task_id": task_id,
            "enable_multi_file_summary": True,
            "target_format": {"value": "plain_text"},
            "summary_length": summary_length,
            "summary_focus": summary_focus,
            "summary_return_top_k": summary_return_top_k
        }

        # 保存入参到 JSON 并初始化任务
        task_manager.create_task_from_request(
            task_id=task_id,
            request_dict=request_dict,
        )

        # 直接执行任务，不使用队列锁
        try:
            await run_in_threadpool(start_job, task_id)
        except Exception:
            logger.exception(f"start_job failed for task_id={task_id}")

        status = task_manager.get_status_from_json(task_id)

        # 从result_data中提取总结结果
        if status.get("result_data") and status["result_data"].get("summary"):
            summary_data = status["result_data"]["summary"]
            status.update({
                "summary": summary_data.get("summary", ""),
                "summary_dict": summary_data.get("summary_dict", {}),
                "summary_meta": summary_data.get("summary_meta")
            })

        return FileSummarizeResponse(**status).model_dump_json(indent=2)

    except Exception as e:
        logger.exception(f"summarize_file_content_tool failed: {str(e)}")
        return f'{{"error": "文件总结失败: {str(e)}"}}'


@mcp.tool()
async def extract_file_content_tool(
    task_id: str,
    purpose: str = "content_reading",
    target_format: str = "plain_text",
    enable_ocr: bool = True,
    extract_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    信息抽取接口（基于LangExtract执行信息抽取，如需会自动调用读取）

    Args:
        task_id: 任务ID
        purpose: 处理目的
        target_format: 目标格式
        enable_ocr: 是否启用OCR
        extract_config: 抽取配置

    Returns:
        JSON格式的抽取结果字符串
    """
    try:
        logger.info(f"extract_file_content_tool: task_id={task_id}")

        # 检查是否已经读取过文件内容
        try:
            # 尝试获取任务状态，如果不存在会抛出异常
            task_manager.get_status_from_json(task_id)
        except Exception:
            # 文件尚未读取，先自动调用读取接口
            logger.info(f"Task {task_id} not found, auto-calling file/read first")
            await read_file_content_tool(
                task_id=task_id,
                purpose=purpose,
                target_format=target_format,
                enable_ocr=enable_ocr
            )

        # 构建包含抽取参数的请求
        from app.api.schemas.file_extract_schemas import LangExtractConfig
        request_dict = {
            "task_id": task_id,
            "purpose": ProcessingPurpose(value=purpose).model_dump(),
            "target_format": OutputFormat(value=target_format).model_dump(),
            "enable_ocr": enable_ocr,
            "ocr_mode": "auto",
            "enable_extract": True,
            "extract_config": extract_config if extract_config else LangExtractConfig(prompt="请抽取文档中的关键信息").model_dump()
        }

        # 保存入参到 JSON 并初始化任务
        task_manager.create_task_from_request(
            task_id=task_id,
            request_dict=request_dict,
        )

        # 直接执行任务，不使用队列锁
        try:
            await run_in_threadpool(start_job, task_id)
        except Exception:
            logger.exception(f"start_job failed for task_id={task_id}")

        status = task_manager.get_status_from_json(task_id)

        # 从result_data中提取抽取结果
        extraction_data = {}
        if status.get("result_data") and status["result_data"].get("extraction"):
            extraction_data = status["result_data"]["extraction"]
            status.update({
                "document_id": extraction_data.get("document_id"),
                "text_length": extraction_data.get("text_length"),
                "extractions": extraction_data.get("extractions", [])
            })

        return FileExtractResponse(**status).model_dump_json(indent=2)

    except Exception as e:
        logger.exception(f"extract_file_content_tool failed: {str(e)}")
        return f'{{"error": "信息抽取失败: {str(e)}"}}'


if __name__ == "__main__":
    mcp.run()