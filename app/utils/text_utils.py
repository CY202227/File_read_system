"""
文本工具模块
Text utilities for handling text content operations
"""

import re
from pathlib import Path
from typing import Tuple, Optional
from fastapi import HTTPException
import aiofiles
from config.settings import settings


def detect_text_format(content: str) -> str:
    """
    自动检测文本格式
    
    Args:
        content: 文本内容
    
    Returns:
        str: 检测到的格式扩展名（如 .html, .md, .txt）
    """
    # 移除首尾空白字符
    content = content.strip()
    
    # HTML检测 - 检查是否包含HTML标签
    html_patterns = [
        r'<!DOCTYPE\s+html>',
        r'<html[^>]*>',
        r'<head[^>]*>',
        r'<body[^>]*>',
        r'<div[^>]*>',
        r'<p[^>]*>',
        r'<span[^>]*>',
        r'<a[^>]*>',
        r'<img[^>]*>',
        r'<script[^>]*>',
        r'<style[^>]*>'
    ]
    
    for pattern in html_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return '.html'
    
    # Markdown检测 - 检查Markdown语法特征
    md_patterns = [
        r'^#{1,6}\s+',  # 标题
        r'\*\*[^*]+\*\*',  # 粗体
        r'\*[^*]+\*',  # 斜体
        r'\[[^\]]+\]\([^)]+\)',  # 链接
        r'!\[[^\]]*\]\([^)]+\)',  # 图片
        r'^\s*[-*+]\s+',  # 无序列表
        r'^\s*\d+\.\s+',  # 有序列表
        r'^\s*>\s+',  # 引用
        r'```[\s\S]*```',  # 代码块
        r'`[^`]+`',  # 行内代码
    ]
    
    lines = content.split('\n')
    md_score = 0
    
    for line in lines:
        for pattern in md_patterns:
            if re.search(pattern, line):
                md_score += 1
                break
    
    # 如果超过30%的行包含Markdown语法，认为是Markdown
    if md_score > len(lines) * 0.3:
        return '.md'
    
    # 默认返回纯文本
    return '.txt'


def validate_extension(extension: str) -> str:
    """
    验证和标准化扩展名
    
    Args:
        extension: 扩展名（可以带或不带点）
    
    Returns:
        str: 标准化后的扩展名（带点）
    """
    # 移除首尾空白字符
    extension = extension.strip()
    
    # 如果没有提供扩展名，返回.txt
    if not extension:
        return '.txt'
    
    # 确保扩展名以点开头
    if not extension.startswith('.'):
        extension = '.' + extension
    
    # 转换为小写
    extension = extension.lower()
    
    # 验证扩展名是否在允许列表中
    ext_without_dot = extension.lstrip('.')
    if ext_without_dot not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件扩展名: {extension}"
        )
    
    return extension


async def save_text_content(
    content: str,
    task_id: str,
    file_uuid: str,
    auto_detect: bool = True,
    extension: Optional[str] = None
) -> Tuple[str, str]:
    """
    保存文本内容到文件
    
    Args:
        content: 文本内容
        task_id: 任务ID
        file_uuid: 文件UUID
        auto_detect: 是否自动检测格式
        extension: 手动模式下的文件扩展名
    
    Returns:
        Tuple[str, str]: (文件路径, 原始文件名)
    """
    # 验证文件大小
    content_size = len(content.encode('utf-8'))
    if not validate_file_size(content_size):
        raise HTTPException(
            status_code=400,
            detail=f"文本内容大小超过限制: {content_size} bytes"
        )
    
    # 确定文件扩展名
    if auto_detect:
        # 自动检测模式
        file_extension = detect_text_format(content)
    else:
        # 手动模式
        if not extension:
            raise HTTPException(
                status_code=400,
                detail="手动模式下必须提供文件扩展名"
            )
        file_extension = validate_extension(extension)
    
    # 生成随机文件名
    original_filename = f"text_{file_uuid}{file_extension}"
    
    # 创建上传目录
    from app.utils.file_utils import create_upload_directory
    upload_dir = create_upload_directory(task_id)
    
    # 生成新文件名
    new_filename = f"{file_uuid}{file_extension}"
    file_path = upload_dir / new_filename
    
    try:
        # 保存文件
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        return str(file_path), original_filename
    
    except Exception as e:
        # 清理已创建的文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"文本文件保存失败: {str(e)}"
        )


def validate_file_size(file_size: int) -> bool:
    """验证文件大小"""
    return file_size <= settings.MAX_FILE_SIZE


def validate_file_extension(filename: str) -> bool:
    """验证文件扩展名是否允许"""
    if not filename:
        return False
    
    ext = Path(filename).suffix.lower().lstrip('.')
    return ext in settings.ALLOWED_EXTENSIONS
