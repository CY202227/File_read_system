"""
文件上传路由
File Upload Routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import hashlib
from datetime import datetime
import logging

from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    file_id: str
    filename: str
    size: int
    content_type: str
    upload_time: datetime
    file_path: str
    file_hash: str


class FileInfo(BaseModel):
    """文件信息模型"""
    file_id: str
    filename: str
    size: int
    content_type: str
    upload_time: datetime
    status: str


def validate_file_extension(filename: str) -> bool:
    """验证文件扩展名"""
    if not filename:
        return False
    
    ext = filename.split('.')[-1].lower()
    return ext in settings.ALLOWED_EXTENSIONS


def calculate_file_hash(file_content: bytes) -> str:
    """计算文件哈希值"""
    return hashlib.md5(file_content).hexdigest()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    上传单个文件
    
    - **file**: 要上传的文件
    """
    
    # 验证文件
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式。支持的格式: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # 读取文件内容
    file_content = await file.read()
    file_size = len(file_content)
    
    # 验证文件大小
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE / (1024*1024):.1f}MB)"
        )
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")
    
    try:
        # 生成文件ID和保存路径
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1].lower()
        safe_filename = f"{file_id}.{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
        
        # 确保上传目录存在
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # 保存文件
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 计算文件哈希
        file_hash = calculate_file_hash(file_content)
        
        logger.info(f"文件上传成功: {file.filename} -> {file_path}")
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            size=file_size,
            content_type=file.content_type or "application/octet-stream",
            upload_time=datetime.now(),
            file_path=file_path,
            file_hash=file_hash
        )
        
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/upload/multiple", response_model=List[FileUploadResponse])
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """
    批量上传多个文件
    
    - **files**: 要上传的文件列表
    """
    
    if len(files) > 10:  # 限制最多10个文件
        raise HTTPException(status_code=400, detail="一次最多上传10个文件")
    
    results = []
    
    for file in files:
        try:
            # 重用单文件上传逻辑
            result = await upload_file(file)
            results.append(result)
        except HTTPException as e:
            # 记录失败的文件，但继续处理其他文件
            logger.warning(f"文件 {file.filename} 上传失败: {e.detail}")
            continue
    
    if not results:
        raise HTTPException(status_code=400, detail="没有文件上传成功")
    
    return results


@router.get("/files", response_model=List[FileInfo])
async def list_uploaded_files():
    """获取已上传文件列表"""
    
    try:
        files = []
        upload_dir = settings.UPLOAD_DIR
        
        if not os.path.exists(upload_dir):
            return files
        
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                
                # 从文件名中提取UUID作为file_id
                file_id = filename.split('.')[0]
                
                files.append(FileInfo(
                    file_id=file_id,
                    filename=filename,
                    size=stat.st_size,
                    content_type="application/octet-stream",
                    upload_time=datetime.fromtimestamp(stat.st_mtime),
                    status="uploaded"
                ))
        
        return sorted(files, key=lambda x: x.upload_time, reverse=True)
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """删除指定文件"""
    
    try:
        upload_dir = settings.UPLOAD_DIR
        
        # 查找对应的文件
        for filename in os.listdir(upload_dir):
            if filename.startswith(file_id):
                file_path = os.path.join(upload_dir, filename)
                os.remove(file_path)
                logger.info(f"文件删除成功: {filename}")
                return {"message": f"文件 {filename} 删除成功"}
        
        raise HTTPException(status_code=404, detail="文件不存在")
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")