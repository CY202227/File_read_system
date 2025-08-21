from openai import OpenAI
import fitz  # PyMuPDF
import numpy as np
import enum
from pydantic import BaseModel, Field
from PIL import Image
from prompts import dict_promptmode_to_prompt
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