"""
文件上传路由
File upload routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pathlib import Path
from typing import Optional, List
import traceback

from app.utils.file_utils import (
    generate_file_uuid, 
    save_uploaded_file, 
    copy_local_file,
    get_file_info,
    validate_file_extension,
)
from app.utils.text_utils import save_text_content
from app.core.task_manager import (
    validate_or_create_task, 
    update_task_status, 
    add_file_to_task,
    TaskStatus,
    TaskPriority
)
from app.api.schemas.upload_schemas import (
    FilePathRequest, 
    UploadResponse, 
    FileUploadInfo,
    TextUploadRequest,
)

router = APIRouter(tags=["文件上传"])


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
                # 以扩展名为准进行校验（content_type 为 MIME 类型，不能用于与扩展名列表比较）
                if not validate_file_extension(file.filename or ""):
                    raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file.filename}")

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


@router.post("/upload/text", response_model=UploadResponse)
async def upload_text_content(
    request: TextUploadRequest
):
    """
    上传纯文本内容
    
    - **content**: 纯文本内容
    - **task_id**: 可选的任务ID，如果不提供将自动生成
    - **priority**: 任务优先级 (1=低, 2=普通, 3=高, 4=紧急)
    - **auto_detect**: 是否自动检测文本格式
    - **extension**: 手动模式下的文件扩展名（仅在auto_detect=false时需要）
    - 返回任务ID和文件信息
    """
    try:
        # 解析优先级
        task_priority = TaskPriority(int(request.priority)) if request.priority else TaskPriority.NORMAL
        
        # 处理task_id，确保空字符串被转换为None
        task_id = request.task_id
        if task_id is not None and task_id.strip() == '':
            task_id = None
        
        # 验证或创建任务ID
        task_id = validate_or_create_task(task_id, priority=task_priority)
        
        # 更新任务状态为活跃
        update_task_status(task_id, TaskStatus.ACTIVE)
        
        # 验证手动模式下的扩展名参数
        if not request.auto_detect and not request.extension:
            raise HTTPException(
                status_code=400,
                detail="手动模式下必须提供文件扩展名"
            )
        
        try:
            file_uuid = generate_file_uuid()
            
            # 保存文本内容
            file_path, original_filename = await save_text_content(
                content=request.content,
                task_id=task_id,
                file_uuid=file_uuid,
                auto_detect=request.auto_detect,
                extension=request.extension
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
            
            return UploadResponse(
                task_id=task_id,
                total_files=1,
                successful_uploads=1,
                failed_uploads=0,
                files=[file_upload_info],
                message=f"文本内容上传成功，文件名: {original_filename}"
            )
            
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
            
            return UploadResponse(
                task_id=task_id,
                total_files=1,
                successful_uploads=0,
                failed_uploads=1,
                files=[file_upload_info],
                message=f"文本内容上传失败: {str(e)}"
            )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 其他异常返回500错误，包含详细的错误信息
        error_detail = f"文本内容上传失败: {str(e)}"
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