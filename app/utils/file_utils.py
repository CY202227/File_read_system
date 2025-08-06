"""
文件工具模块
File utilities for handling file operations
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
import aiofiles
from config.settings import settings


def generate_task_id() -> str:
    """生成任务ID"""
    return str(uuid.uuid4())


def generate_file_uuid() -> str:
    """生成文件UUID"""
    return str(uuid.uuid4())


def create_upload_directory(task_id: str) -> Path:
    """为任务创建上传目录"""
    upload_dir = Path(settings.UPLOAD_DIR) / task_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_safe_filename(filename: str) -> str:
    """获取安全的文件名"""
    # 移除路径分隔符和特殊字符
    safe_name = os.path.basename(filename)
    # 移除或替换不安全的字符
    unsafe_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')
    return safe_name


def validate_file_extension(filename: str) -> bool:
    """验证文件扩展名是否允许"""
    if not filename:
        return False
    
    ext = Path(filename).suffix.lower().lstrip('.')
    return ext in settings.ALLOWED_EXTENSIONS


def validate_file_size(file_size: int) -> bool:
    """验证文件大小"""
    return file_size <= settings.MAX_FILE_SIZE


async def save_uploaded_file(
    upload_file: UploadFile, 
    task_id: str, 
    file_uuid: str
) -> Tuple[str, str]:
    """
    保存上传的文件
    
    Args:
        upload_file: FastAPI上传文件对象
        task_id: 任务ID
        file_uuid: 文件UUID
    
    Returns:
        Tuple[str, str]: (文件路径, 原始文件名)
    """
    # 验证文件扩展名
    if not validate_file_extension(upload_file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式: {upload_file.filename}"
        )
    
    # 创建上传目录
    upload_dir = create_upload_directory(task_id)
    
    # 生成安全的文件名
    original_filename = get_safe_filename(upload_file.filename)
    file_extension = Path(original_filename).suffix
    
    # 使用UUID前缀的新文件名
    new_filename = f"{file_uuid}{file_extension}"
    file_path = upload_dir / new_filename
    
    # 保存文件
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await upload_file.read()
            
            # 验证文件大小
            if not validate_file_size(len(content)):
                raise HTTPException(
                    status_code=400,
                    detail=f"文件大小超过限制: {len(content)} bytes"
                )
            
            await f.write(content)
        
        return str(file_path), original_filename
    
    except Exception as e:
        # 清理已创建的文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"文件保存失败: {str(e)}"
        )


async def copy_local_file(
    source_path: str, 
    task_id: str, 
    file_uuid: str
) -> Tuple[str, str]:
    """
    复制本地文件到上传目录
    
    Args:
        source_path: 源文件路径
        task_id: 任务ID
        file_uuid: 文件UUID
    
    Returns:
        Tuple[str, str]: (文件路径, 原始文件名)
    """
    source_path = Path(source_path)
    
    # 验证源文件是否存在
    if not source_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"文件不存在: {source_path}"
        )
    
    # 验证文件扩展名
    if not validate_file_extension(source_path.name):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {source_path.name}"
        )
    
    # 验证文件大小
    file_size = source_path.stat().st_size
    if not validate_file_size(file_size):
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制: {file_size} bytes"
        )
    
    # 创建上传目录
    upload_dir = create_upload_directory(task_id)
    
    # 生成新文件名
    original_filename = source_path.name
    file_extension = source_path.suffix
    new_filename = f"{file_uuid}{file_extension}"
    dest_path = upload_dir / new_filename
    
    try:
        # 复制文件
        shutil.copy2(source_path, dest_path)
        return str(dest_path), original_filename
    
    except Exception as e:
        # 清理已创建的文件
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"文件复制失败: {str(e)}"
        )


def get_file_info(file_path: str) -> dict:
    """获取文件信息"""
    path = Path(file_path)
    if not path.exists():
        return {}
    
    stat = path.stat()
    return {
        "filename": path.name,
        "size": stat.st_size,
        "created_time": stat.st_ctime,
        "modified_time": stat.st_mtime,
        "extension": path.suffix.lower()
    } 