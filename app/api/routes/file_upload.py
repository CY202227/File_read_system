"""
文件上传路由
File upload routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Optional, List
import traceback

from app.utils.file_utils import (
    generate_task_id, 
    generate_file_uuid, 
    save_uploaded_file, 
    copy_local_file,
    get_file_info
)
from app.core.task_manager import (
    validate_or_create_task, 
    update_task_status, 
    add_file_to_task,
    TaskStatus,
    TaskPriority
)
from app.api.schemas.upload import (
    FilePathRequest, 
    UploadResponse, 
    FileUploadInfo,
    ErrorResponse
)

router = APIRouter(prefix="/api", tags=["文件上传"])


@router.post("/upload/stream", response_model=UploadResponse)
async def upload_files_stream(
    files: List[UploadFile] = File(..., description="要上传的文件列表（支持单个或多个文件）"),
    task_id: Optional[str] = Form(None, description="可选的任务ID，如果不提供将自动生成"),
    priority: Optional[str] = Form(TaskPriority.NORMAL.value, description="任务优先级")
):
    """
    通过文件流上传文件（支持单个或多个文件）
    
    - **files**: 要上传的文件列表
    - **task_id**: 可选的任务ID，如果不提供将自动生成，如果提供则验证是否存在
    - **priority**: 任务优先级 (1=低, 2=普通, 3=高, 4=紧急)
    - 返回任务ID和所有文件信息
    """
    try:
        # 解析优先级
        task_priority = TaskPriority(int(priority)) if priority else TaskPriority.NORMAL
        
        # 处理task_id，确保空字符串被转换为None
        if task_id is not None and task_id.strip() == '':
            task_id = None
        
        # 验证或创建任务ID
        # 如果提供了task_id，会验证是否存在；如果没有提供，会创建新的
        task_id = validate_or_create_task(task_id, priority=task_priority)
        
        # 更新任务状态为活跃
        update_task_status(task_id, TaskStatus.ACTIVE)
        
        file_uploads = []
        successful_count = 0
        failed_count = 0
        
        for file in files:
            try:
                file_uuid = generate_file_uuid()
                
                # 保存上传的文件
                file_path, original_filename = await save_uploaded_file(
                    upload_file=file,
                    task_id=task_id,
                    file_uuid=file_uuid
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
                
                file_uploads.append(file_upload_info)
                successful_count += 1
                
                # 向任务管理器添加文件信息
                add_file_to_task(task_id, {
                    "file_uuid": file_uuid,
                    "original_filename": original_filename,
                    "file_path": file_path,
                    "file_size": file_info.get("size", 0),
                    "status": "success",
                    "uploaded_at": str(file_info.get("created_time", ""))
                })
                
            except Exception as e:
                file_upload_info = FileUploadInfo(
                    file_uuid=generate_file_uuid(),
                    original_filename=file.filename or "unknown",
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
        
        return UploadResponse(
            task_id=task_id,
            total_files=len(files),
            successful_uploads=successful_count,
            failed_uploads=failed_count,
            files=file_uploads,
            message=f"文件上传完成，成功: {successful_count}, 失败: {failed_count}"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 其他异常返回500错误，包含详细的错误信息
        error_detail = f"文件上传失败: {str(e)}"
        if hasattr(e, '__traceback__'):
            error_detail += f"\nTraceback: {traceback.format_exc()}"
        
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@router.post("/upload/file", response_model=UploadResponse)
async def upload_files_by_path(
    request: FilePathRequest
):
    """
    通过文件路径上传文件（支持单个或多个文件）
    
    - **file_paths**: 文件路径列表（支持单个或多个文件）
    - **task_id**: 可选的任务ID，如果不提供将自动生成，如果提供则验证是否存在
    - 返回任务ID和所有文件信息
    """
    try:
        # 验证或创建任务ID
        # 如果提供了task_id，会验证是否存在；如果没有提供，会创建新的
        task_id = validate_or_create_task(request.task_id)
        
        # 更新任务状态为活跃
        update_task_status(task_id, TaskStatus.ACTIVE)
        
        file_uploads = []
        successful_count = 0
        failed_count = 0
        
        for file_path in request.file_paths:
            try:
                file_uuid = generate_file_uuid()
                
                # 复制文件
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
        
        return UploadResponse(
            task_id=task_id,
            total_files=len(request.file_paths),
            successful_uploads=successful_count,
            failed_uploads=failed_count,
            files=file_uploads,
            message=f"文件路径上传完成，成功: {successful_count}, 失败: {failed_count}"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 其他异常返回500错误，包含详细的错误信息
        error_detail = f"文件路径上传失败: {str(e)}"
        if hasattr(e, '__traceback__'):
            error_detail += f"\nTraceback: {traceback.format_exc()}"
        
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )