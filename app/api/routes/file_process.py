from typing import AsyncIterator, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from config.logging_config import get_logger
from app.core.task_manager import TaskManager
from app.core.job_manager import start_job
from app.api.schemas.file_process_schemas import (
    FileProcessRequest,
    FileProcessResponse
)


router = APIRouter()
logger = get_logger(__name__)
task_manager = TaskManager()


@router.post("/file/process", response_model=FileProcessResponse, summary="提交文件处理任务")
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
    # TODO: enqueue_process_task(request)
    try:
        start_job(request.task_id)
    except Exception:
        logger.exception("start_job failed for task_id=%s", request.task_id)
    status = task_manager.get_status_from_json(request.task_id)
    return FileProcessResponse(**status)


@router.get("/file/tasks/{task_id}", response_model=FileProcessResponse, summary="查询任务状态/结果")
async def get_task_status(task_id: str) -> FileProcessResponse:
    """查询任务状态与结果（若已完成）。

    TODO:
    - fetch_task_status(task_id)
    - 当完成时填充 result_url 或 result_data
    """
    logger.debug("get_task_status: task_id=%s", task_id)

    status = task_manager.get_status_from_json(task_id)
    return FileProcessResponse(**status)


@router.get("/file/summary/stream/{task_id}", summary="Summary SSE 流式返回")
async def stream_summary(task_id: str) -> StreamingResponse:
    """流式返回 summary 结果（SSE）。

    TODO:
    - 使用 Redis Streams/PubSub 订阅 summary:{task_id} 的增量事件
    - 将事件转为 SSE 规范：id/event/data
    - 支持心跳与断线重连（Last-Event-ID）
    """
    logger.info("stream_summary: task_id=%s", task_id)

    async def event_generator() -> AsyncIterator[str]:
        # TODO: 替换为真实的事件订阅循环
        yield "event: start\ndata: {\"started\": true}\n\n"
        # 结束占位
        yield "event: done\ndata: {\"summary\": []}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


