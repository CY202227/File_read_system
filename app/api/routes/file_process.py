import asyncio
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from config.logging_config import get_logger
from app.core.task_manager import task_manager as task_manager
from app.core.job_manager import start_job
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
    FileChunkRequest,
    FileChunkResponse
)
from app.api.schemas.file_summarize_schemas import (
    FileSummarizeRequest,
    FileSummarizeResponse
)
from app.api.schemas.file_extract_schemas import (
    FileExtractRequest,
    FileExtractResponse
)
from app.utils.log_utils import log_call

router = APIRouter()
logger = get_logger(__name__)

# 进程内串行队列锁：保证同一进程内按提交顺序依次处理
_queue_lock = asyncio.Lock()


@router.post("/file/process", response_model=FileProcessResponse, summary="提交文件处理任务（同步：内部队列顺序执行，完成后直接返回结果）")
async def submit_file_process(request: FileProcessRequest) -> FileProcessResponse:
    """接受文件处理请求并创建任务。

    TODO:
    - enqueue_process_task(request)
    - if request.target_format.value == "summary" and request.summary_streaming: return SSE endpoint URL
    """
    logger.info("submit_file_process: task_id=%s", request.task_id)

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
            logger.exception("start_job failed for task_id=%s", request.task_id)

    status = task_manager.get_status_from_json(request.task_id)
    return FileProcessResponse(**status)

@log_call
@router.post("/file/read", response_model=FileReadResponse, summary="文件内容读取接口（仅执行文件读取步骤）")
async def read_file_content(request: FileReadRequest) -> FileReadResponse:
    """接受文件读取请求并执行文件内容读取。
    
    此接口仅执行文件读取步骤，不执行切片和总结等后续处理。
    """
    logger.info("read_file_content: task_id=%s", request.task_id)
    
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
            logger.exception("start_job failed for task_id=%s", request.task_id)
    
    status = task_manager.get_status_from_json(request.task_id)
    return FileReadResponse(**status)

@router.post("/file/chunk", response_model=FileChunkResponse, summary="文件切片接口（执行文件切片步骤，如需会自动调用读取）")
async def chunk_file_content(request: FileChunkRequest) -> FileChunkResponse:
    """接受文件切片请求并执行文件切片。
    
    此接口会检查是否已经调用过 /file/read 接口读取文件内容，如果没有会自动调用读取步骤。
    """
    logger.info("chunk_file_content: task_id=%s", request.task_id)
    
    # 检查是否已经读取过文件内容
    try:
        # 尝试获取任务状态，如果不存在会抛出异常
        task_manager.get_status_from_json(request.task_id)
    except Exception:
        # 文件尚未读取，先自动调用读取接口
        logger.info(f"Task {request.task_id} not found, auto-calling file/read first")
        read_request = FileReadRequest(
            task_id=request.task_id,
            purpose=ProcessingPurpose(value="content_reading"),
            target_format=OutputFormat(value="plain_text"),
            enable_ocr=True
        )
        await read_file_content(read_request)
    
    # 构建包含切片参数的请求
    request_dict = request.model_dump(mode="json")
    request_dict.update({
        "enable_chunking": True,
        "target_format": {"value": "plain_text"},  # 使用支持的格式
        "chunking_strategy": request.chunking_strategy.model_dump(),
        "chunk_size": request.chunk_size,
        "chunk_overlap": request.chunk_overlap,
        "chunking_config": request.chunking_config.model_dump() if request.chunking_config else {}
    })
    
    # 保存入参到 JSON 并初始化任务
    task_manager.create_task_from_request(
        task_id=request.task_id,
        request_dict=request_dict,
    )
    
    # 直接执行任务，不使用队列锁
    try:
        await run_in_threadpool(start_job, request.task_id)
    except Exception:
        logger.exception("start_job failed for task_id=%s", request.task_id)

    status = task_manager.get_status_from_json(request.task_id)
    
    # 从result_data中提取切片结果
    if status.get("result_data") and status["result_data"].get("chunking"):
        chunking_data = status["result_data"]["chunking"]
        status.update({
            "chunks": chunking_data.get("chunks"),
            "derivatives": chunking_data.get("derivatives"),
            "per_file": chunking_data.get("per_file"),
            "chunks_meta": chunking_data.get("chunks_meta")
        })
        print(status)
    return FileChunkResponse(**status)


@router.post("/file/summarize", response_model=FileSummarizeResponse, summary="文件总结接口（执行文件总结步骤，如需会自动调用读取）")
async def summarize_file_content(request: FileSummarizeRequest) -> FileSummarizeResponse:
    """接受文件总结请求并执行文件总结。
    
    此接口会检查是否已经调用过 /file/read 接口读取文件内容，如果没有会自动调用读取步骤。
    可以直接使用 /file/read 的结果，也可以使用 /file/chunk 的结果进行总结。
    """
    logger.info("summarize_file_content: task_id=%s", request.task_id)
    
    # 检查是否已经读取过文件内容
    try:
        # 尝试获取任务状态，如果不存在会抛出异常
        task_manager.get_status_from_json(request.task_id)
    except Exception:
        # 文件尚未读取，先自动调用读取接口
        logger.info(f"Task {request.task_id} not found, auto-calling file/read first")
        read_request = FileReadRequest(
            task_id=request.task_id,
            purpose=ProcessingPurpose(value="content_reading"),
            target_format=OutputFormat(value="plain_text"),
            enable_ocr=True
        )
        await read_file_content(read_request)
    
    # 构建包含总结参数的请求
    request_dict = request.model_dump(mode="json")
    request_dict.update({
        "enable_multi_file_summary": True,
        "target_format": {"value": "plain_text"},  # 使用支持的格式
        "summary_length": request.summary_length,
        "summary_focus": request.summary_focus,
        "summary_return_top_k": request.summary_return_top_k
    })
    
    # 保存入参到 JSON 并初始化任务
    task_manager.create_task_from_request(
        task_id=request.task_id,
        request_dict=request_dict,
    )
    
    # 直接执行任务，不使用队列锁
    try:
        await run_in_threadpool(start_job, request.task_id)
    except Exception:
        logger.exception("start_job failed for task_id=%s", request.task_id)

    status = task_manager.get_status_from_json(request.task_id)
    
    # 从result_data中提取总结结果
    if status.get("result_data") and status["result_data"].get("summary"):
        summary_data = status["result_data"]["summary"]
        status.update({
            "summary": summary_data.get("summary", ""),
            "summary_dict": summary_data.get("summary_dict", {}),
            "summary_meta": summary_data.get("summary_meta")
        })
    
    return FileSummarizeResponse(**status)


@router.post("/file/extract", response_model=FileExtractResponse, summary="信息抽取接口（基于LangExtract执行信息抽取，如需会自动调用读取）")
async def extract_file_content(request: FileExtractRequest) -> FileExtractResponse:
    """接受信息抽取请求并执行基于LangExtract的信息抽取。
    
    此接口会检查是否已经调用过 /file/read 接口读取文件内容，如果没有会自动调用读取步骤。
    基于LangExtract库实现，支持从文本中抽取结构化信息，如人物、事件、地点等。
    """
    logger.info("extract_file_content: task_id=%s", request.task_id)
    
    # 检查是否已经读取过文件内容
    try:
        # 尝试获取任务状态，如果不存在会抛出异常
        task_manager.get_status_from_json(request.task_id)
    except Exception:
        # 文件尚未读取，先自动调用读取接口
        logger.info(f"Task {request.task_id} not found, auto-calling file/read first")
        read_request = FileReadRequest(
            task_id=request.task_id,
            purpose=request.purpose,
            target_format=request.target_format,
            enable_ocr=request.enable_ocr,
            ocr_mode=request.ocr_mode
        )
        await read_file_content(read_request)
    
    # 构建包含抽取参数的请求
    request_dict = request.model_dump(mode="json")
    request_dict.update({
        "enable_extract": True,
        "extract_config": request.extract_config.model_dump()
    })
    
    # 保存入参到 JSON 并初始化任务
    task_manager.create_task_from_request(
        task_id=request.task_id,
        request_dict=request_dict,
    )
    
    # 直接执行任务，不使用队列锁
    try:
        await run_in_threadpool(start_job, request.task_id)
    except Exception:
        logger.exception("start_job failed for task_id=%s", request.task_id)

    status = task_manager.get_status_from_json(request.task_id)
    
    # 从result_data中提取抽取结果
    extraction_data = {}
    if status.get("result_data") and status["result_data"].get("extraction"):
        extraction_data = status["result_data"]["extraction"]
        status.update({
            "document_id": extraction_data.get("document_id"),
            "text_length": extraction_data.get("text_length"),
            "extractions": extraction_data.get("extractions", [])
        })
    
    return FileExtractResponse(**status)