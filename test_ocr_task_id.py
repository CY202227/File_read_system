#!/usr/bin/env python3
"""
测试OCR任务ID功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.parsers.file_read.ocr_read import OCRReader
from config.settings import settings

def test_ocr_task_id():
    """测试OCR任务ID功能"""
    
    # 设置测试用的OCR配置（如果没有设置的话）
    if not settings.OCR_MODEL_URL:
        print("警告: OCR_MODEL_URL 未设置，跳过实际OCR测试")
        return
    
    if not settings.OCR_MODEL_API_KEY:
        print("警告: OCR_MODEL_API_KEY 未设置，跳过实际OCR测试")
        return
    
    # 创建测试任务ID
    task_id = "test_task_12345"
    
    # 检查测试PDF文件
    test_pdf = "test.pdf"
    if not os.path.exists(test_pdf):
        print(f"测试文件 {test_pdf} 不存在，跳过测试")
        return
    
    print(f"开始测试OCR任务ID功能...")
    print(f"任务ID: {task_id}")
    print(f"测试文件: {test_pdf}")
    
    try:
        # 初始化OCR读取器
        ocr_reader = OCRReader(ocr_mode="prompt_ocr")
        print("OCR读取器初始化成功")
        
        # 测试PDF转图片功能
        print("测试PDF转图片功能...")
        images = ocr_reader.load_images_from_pdf(test_pdf, dpi=200)
        print(f"成功加载 {len(images)} 页图片")
        
        # 检查图片保存目录
        task_dir = Path(settings.STATIC_DIR) / "ocr_temp" / task_id
        print(f"任务目录: {task_dir}")
        
        # 测试OCR处理（会保存图片到任务目录）
        if images:
            print("测试OCR处理第一页...")
            ocr_text = ocr_reader.process_image_with_ocr(images[0], task_id=task_id)
            print(f"OCR处理完成，获取到 {len(ocr_text)} 字符")
            
            # 检查图片是否保存到任务目录
            if task_dir.exists():
                saved_images = list(task_dir.glob("*.png"))
                print(f"任务目录中找到 {len(saved_images)} 个图片文件:")
                for img in saved_images:
                    print(f"  - {img.name}")
            else:
                print("任务目录不存在")
        
        print("测试完成！")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ocr_task_id()
