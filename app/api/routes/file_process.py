"""
文件处理路由
File processing routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Optional

from app.utils.file_utils import (
    generate_task_id, 
    generate_file_uuid, 
    save_uploaded_file, 
    copy_local_file,
    get_file_info
)
from app.api.schemas.upload import (
    FilePathRequest, 
    UploadResponse, 
    ErrorResponse
)

router = APIRouter(prefix="/api", tags=["文件处理"])


@router.post("/upload/stream", response_model=UploadResponse)
async def upload_file_stream(
    file: UploadFile = File(..., description="上传的文件")
):
    """
    通过文件流上传文件
    
    - **file**: 要上传的文件
    - 返回任务ID和文件信息
    """
    try:
        # 生成任务ID和文件UUID
        task_id = generate_task_id()
        file_uuid = generate_file_uuid()
        
        # 保存上传的文件
        file_path, original_filename = await save_uploaded_file(
            upload_file=file,
            task_id=task_id,
            file_uuid=file_uuid
        )
        
        # 获取文件信息
        file_info = get_file_info(file_path)
        
        return UploadResponse(
            task_id=task_id,
            file_uuid=file_uuid,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_info.get("size", 0),
            message="文件上传成功"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 其他异常返回500错误
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )


@router.post("/upload/file", response_model=UploadResponse)
async def upload_local_file(
    request: FilePathRequest
):
    """
    通过本地文件路径上传文件
    
    - **file_path**: 本地文件路径
    - 返回任务ID和文件信息
    """
    try:
        # 生成任务ID和文件UUID
        task_id = generate_task_id()
        file_uuid = generate_file_uuid()
        
        # 复制本地文件
        file_path, original_filename = await copy_local_file(
            source_path=request.file_path,
            task_id=task_id,
            file_uuid=file_uuid
        )
        
        # 获取文件信息
        file_info = get_file_info(file_path)
        
        return UploadResponse(
            task_id=task_id,
            file_uuid=file_uuid,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_info.get("size", 0),
            message="本地文件上传成功"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 其他异常返回500错误
        raise HTTPException(
            status_code=500,
            detail=f"本地文件上传失败: {str(e)}"
        )


@router.post("/upload/path", response_model=UploadResponse)
async def upload_server_path(
    request: FilePathRequest
):
    """
    通过服务器文件路径上传文件
    
    - **file_path**: 服务器上的文件路径
    - 返回任务ID和文件信息
    """
    try:
        # 生成任务ID和文件UUID
        task_id = generate_task_id()
        file_uuid = generate_file_uuid()
        
        # 复制服务器文件
        file_path, original_filename = await copy_local_file(
            source_path=request.file_path,
            task_id=task_id,
            file_uuid=file_uuid
        )
        
        # 获取文件信息
        file_info = get_file_info(file_path)
        
        return UploadResponse(
            task_id=task_id,
            file_uuid=file_uuid,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_info.get("size", 0),
            message="服务器文件上传成功"
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 其他异常返回500错误
        raise HTTPException(
            status_code=500,
            detail=f"服务器文件上传失败: {str(e)}"
        )


@router.post("/upload/unified", response_model=UploadResponse)
async def unified_upload(
    file: Optional[UploadFile] = File(None, description="上传的文件流"),
    file_path: Optional[str] = None,
    server_path: Optional[str] = None
):
    """
    统一的上传接口，支持三种上传方式
    
    - **file**: 文件流上传
    - **file_path**: 本地文件路径
    - **server_path**: 服务器文件路径
    
    至少需要提供一种上传方式
    """
    try:
        # 验证参数
        upload_methods = []
        if file:
            upload_methods.append("stream")
        if file_path:
            upload_methods.append("file")
        if server_path:
            upload_methods.append("server")
            
        if len(upload_methods) == 0:
            raise HTTPException(
                status_code=400,
                detail="请提供至少一种上传方式：file（文件流）、file_path（本地路径）或server_path（服务器路径）"
            )
            
        if len(upload_methods) > 1:
            raise HTTPException(
                status_code=400,
                detail="只能提供一种上传方式，请选择：file（文件流）、file_path（本地路径）或server_path（服务器路径）"
            )
        
        # 生成任务ID和文件UUID
        task_id = generate_task_id()
        file_uuid = generate_file_uuid()
        
        # 根据上传方式处理文件
        if file:
            # 文件流上传
            file_path, original_filename = await save_uploaded_file(
                upload_file=file,
                task_id=task_id,
                file_uuid=file_uuid
            )
            message = "文件流上传成功"
            
        elif file_path:
            # 本地文件路径上传
            file_path, original_filename = await copy_local_file(
                source_path=file_path,
                task_id=task_id,
                file_uuid=file_uuid
            )
            message = "本地文件上传成功"
            
        elif server_path:
            # 服务器文件路径上传
            file_path, original_filename = await copy_local_file(
                source_path=server_path,
                task_id=task_id,
                file_uuid=file_uuid
            )
            message = "服务器文件上传成功"
        
        # 获取文件信息
        file_info = get_file_info(file_path)
        
        return UploadResponse(
            task_id=task_id,
            file_uuid=file_uuid,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_info.get("size", 0),
            message=message
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        # 其他异常返回500错误
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )


@router.get("/task/{task_id}/info")
async def get_task_info(task_id: str):
    """
    获取任务信息
    
    - **task_id**: 任务ID
    """
    try:
        # 构建任务目录路径
        task_dir = Path("uploads") / task_id
        
        if not task_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"任务不存在: {task_id}"
            )
        
        # 获取任务目录下的文件信息
        files = []
        for file_path in task_dir.iterdir():
            if file_path.is_file():
                file_path_str = str(file_path)
                file_info = get_file_info(file_path_str)
                if file_info:  # 确保file_info不为空
                    files.append({
                        "filename": file_info.get("filename", ""),
                        "size": file_info.get("size", 0),
                        "extension": file_info.get("extension", ""),
                        "created_time": file_info.get("created_time", 0)
                    })
        
        return {
            "task_id": task_id,
            "task_dir": str(task_dir),
            "files": files,
            "file_count": len(files)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取任务信息失败: {str(e)}"
        )
