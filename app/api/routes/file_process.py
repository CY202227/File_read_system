import asyncio
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from config.logging_config import get_logger
from app.core.task_manager import task_manager as task_manager
from app.core.job_manager import start_job
from app.api.schemas.file_process_schemas import (
    FileProcessRequest,
    FileProcessResponse
)


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




