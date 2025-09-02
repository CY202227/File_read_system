from openai import OpenAI
import fitz  # PyMuPDF
import numpy as np
import enum
from pydantic import BaseModel, Field
from PIL import Image
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import settings

# 使用配置文件中的设置，它会自动加载 .env 文件
url = settings.OCR_MODEL_URL
api_key = settings.OCR_MODEL_API_KEY
print(f"OCR URL: {url}")
print(f"OCR API Key: {api_key}")
client = OpenAI(base_url=url, api_key=api_key)

class SupportedPdfParseMethod(enum.Enum):
    OCR = 'ocr'
    TXT = 'txt'


class PageInfo(BaseModel):
    """The width and height of page
    """
    w: float = Field(description='the width of page')
    h: float = Field(description='the height of page')


def fitz_doc_to_image(doc, target_dpi=200, origin_dpi=None) -> dict:
    """Convert fitz.Document to image, Then convert the image to numpy array.

    Args:
        doc (_type_): pymudoc page
        dpi (int, optional): reset the dpi of dpi. Defaults to 200.

    Returns:
        dict:  {'img': numpy array, 'width': width, 'height': height }
    """
    mat = fitz.Matrix(target_dpi / 72, target_dpi / 72)
    pm = doc.get_pixmap(matrix=mat, alpha=False)

    if pm.width > 4500 or pm.height > 4500:
        mat = fitz.Matrix(72 / 72, 72 / 72)  # use fitz default dpi
        pm = doc.get_pixmap(matrix=mat, alpha=False)

    image = Image.frombytes('RGB', (pm.width, pm.height), pm.samples)
    return image


def load_images_from_pdf(pdf_file, dpi=200, start_page_id=0, end_page_id=None) -> list:
    images = []
    with fitz.open(pdf_file) as doc:
        pdf_page_num = doc.page_count
        end_page_id = (
            end_page_id
            if end_page_id is not None and end_page_id >= 0
            else pdf_page_num - 1
        )
        if end_page_id > pdf_page_num - 1:
            print('end_page_id is out of range, use images length')
            end_page_id = pdf_page_num - 1

        for index in range(0, doc.page_count):
            if start_page_id <= index <= end_page_id:
                page = doc[index]
                img = fitz_doc_to_image(page, target_dpi=dpi)
                images.append(img)
    return images


# response = client.chat.completions.create(
#     model="ocr",
#     messages=[{
#         "role": "user",
#         "content": [
#             {"type": "text", "text": dict_promptmode_to_prompt["prompt_layout_all_en"]},
#             {
#                 "type": "image_url",
#                 "image_url": {
#                     "url": "https://youke1.picui.cn/s1/2025/08/20/68a570b636ec0.png",
#                 },
#             },
#         ],
#     }],
# )

# print(response.choices[0].message.content)

# 测试并发OCR处理和Base64编码
if __name__ == "__main__":
    import time
    from app.parsers.file_read.ocr_read import OCRReader
    from PIL import Image
    import io

    # 创建OCR读取器
    ocr_reader = OCRReader(ocr_mode="prompt_ocr")

    print("=== 测试Base64图片转换功能 ===")
    # 创建一个测试图片
    test_image = Image.new('RGB', (100, 100), color='red')

    # 测试Base64转换
    base64_str = ocr_reader.image_to_base64(test_image)
    print(f"Base64字符串长度: {len(base64_str)}")
    print(f"Base64前缀: {base64_str[:50]}...")

    # 测试文件路径（请替换为实际的多页PDF文件路径）
    test_pdf_path = "path/to/your/multi_page.pdf"  # 请替换为实际路径

    if os.path.exists(test_pdf_path):
        print("\n=== 测试并发OCR处理 ===")
        print("开始测试并发OCR处理...")
        start_time = time.time()

        # 测试并发处理
        result = ocr_reader.read_pdf_with_ocr(test_pdf_path, task_id="test_concurrent")

        end_time = time.time()
        print(".2f")
        print(f"处理完成，文本长度: {len(result)}")

        # 测试Base64模式
        print("\n=== 测试Base64模式处理 ===")
        start_time = time.time()

        # 加载第一页进行Base64测试
        images = ocr_reader.load_images_from_pdf(test_pdf_path, dpi=200)
        if images:
            result_base64 = ocr_reader.process_image_with_ocr(images[0], task_id="test_base64", use_base64=True)
            end_time = time.time()
            print(".2f")
            print(f"Base64处理完成，文本长度: {len(result_base64)}")

            # 对比URL模式
            result_url = ocr_reader.process_image_with_ocr(images[0], task_id="test_url", use_base64=False)
            end_time = time.time()
            print(".2f")
            print(f"URL处理完成，文本长度: {len(result_url)}")
    else:
        print("测试PDF文件不存在，请设置正确的路径")
        print("但Base64功能测试已完成！")