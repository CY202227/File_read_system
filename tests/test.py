import os
import zipfile
import xmltodict
from reportlab.lib.pagesizes import A4
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

def unzip_file(zip_path, unzip_path=None):
    if not unzip_path:
        unzip_path = zip_path.split('.')[0]
    with zipfile.ZipFile(zip_path, 'r') as f:
        for file in f.namelist():
            f.extract(file, path=unzip_path)
    print(unzip_path)
    return unzip_path

def parse_ofd(file_path):
    unzip_path = unzip_file(file_path)
    
    # 读取OFD.xml获取文档信息
    xml_path = f"{unzip_path}/OFD.xml"
    data_dict = {}
    with open(xml_path, "r", encoding="utf-8") as f:
        _text = f.read()

    print("="*64)
    print("OFD.xml文件内容:")
    print("="*64)
    print(_text)
    print("="*64)

    tree = xmltodict.parse(_text)
    print("解析后的字典结构:")
    print("="*64)
    print(tree)
    print("="*64)
    
    # 处理CustomData，如果是单个对象则直接处理，如果是列表则遍历
    custom_data = tree['ofd:OFD']['ofd:DocBody']['ofd:DocInfo']['ofd:CustomDatas']['ofd:CustomData']
    print("CustomData内容:")
    print("="*64)
    if isinstance(custom_data, list):
        for row in custom_data:
            name = row['@Name']
            text = row.get('#text')
            print(f"Name: {name}")
            print(f"Text: {text}")
            data_dict[name] = text
    else:
        # 单个CustomData对象
        name = custom_data['@Name']
        text = custom_data.get('#text')
        print(f"Name: {name}")
        print(f"Text: {text}")
        data_dict[name] = text
    print("="*64)
    
    # 读取文档内容
    doc_root = tree['ofd:OFD']['ofd:DocBody']['ofd:DocRoot']
    content_path = f"{unzip_path}/{doc_root.replace('Document.xml', 'Pages/Page_0/Content.xml')}"
    
    print("="*64)
    print("Content.xml文件路径:")
    print(content_path)
    print("="*64)
    
    # 读取Content.xml获取文本内容
    with open(content_path, "r", encoding="utf-8") as f:
        content_text = f.read()
    
    print("="*64)
    print("Content.xml文件内容:")
    print("="*64)
    print(content_text)
    print("="*64)
    
    # 解析Content.xml提取文本和格式信息
    content_tree = xmltodict.parse(content_text)
    text_objects = []
    
    # 递归提取所有TextObject标签中的文本和格式信息
    def extract_text_objects(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == 'ofd:TextObject':
                    if isinstance(value, list):
                        for item in value:
                            text_objects.append(item)
                    else:
                        text_objects.append(value)
                else:
                    extract_text_objects(value)
        elif isinstance(obj, list):
            for item in obj:
                extract_text_objects(item)
    
    extract_text_objects(content_tree)
    
    print("="*64)
    print("提取的文本对象:")
    print("="*64)
    for i, obj in enumerate(text_objects):
        print(f"{i+1}: {obj}")
    print("="*64)
    
    data_dict['text_objects'] = text_objects
    data_dict['unzip_path'] = unzip_path
    return data_dict

def ofd_to_pdf(file_path, output_path=None):
    """将OFD文件转换为PDF，使用PyMuPDF保持原始格式"""
    if not output_path:
        output_path = file_path.replace('.ofd', '.pdf')

    try:
        # 首先尝试使用PyMuPDF直接转换
        print("正在尝试使用PyMuPDF转换...")
        doc = fitz.open(file_path)

        # 如果成功打开，尝试转换为PDF
        if len(doc) > 0:
            # 创建新的PDF文档
            pdf_doc = fitz.open()

            # 遍历所有页面
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # 将页面转换为PDF
                pdf_bytes = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("pdf")

                # 创建新页面
                pdf_page = pdf_doc.new_page(width=page.rect.width, height=page.rect.height)

                # 插入页面内容
                temp_doc = fitz.open("pdf", pdf_bytes)
                if len(temp_doc) > 0:
                    pdf_page.show_pdf_page(page.rect, temp_doc, 0)
                temp_doc.close()

            # 保存PDF
            pdf_doc.save(output_path)
            pdf_doc.close()
            doc.close()

            print(f"PDF已生成: {output_path}")
            return output_path
        else:
            raise ValueError("OFD文件无有效页面")

    except Exception as e:
        print(f"PyMuPDF转换失败: {e}")
        print("正在使用备用方案：基于XML解析生成图片")
        return ofd_to_images_fallback(file_path, output_path.replace('.pdf', '_images'))

def ofd_to_images(file_path, output_dir=None):
    """将OFD文件的每一页转换为图片"""
    if not output_dir:
        output_dir = file_path.replace('.ofd', '_images')

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 使用PyMuPDF打开OFD文件
        doc = fitz.open(file_path)

        image_paths = []

        # 遍历所有页面
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # 将页面转换为图片
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x缩放以提高质量

            # 保存图片
            image_path = os.path.join(output_dir, f'page_{page_num + 1:03d}.png')
            pix.save(image_path)

            image_paths.append(image_path)
            print(f"页面 {page_num + 1} 已转换为图片: {image_path}")

        doc.close()

        print(f"所有页面已转换为图片，保存在: {output_dir}")
        return image_paths

    except Exception as e:
        print(f"OFD转图片失败: {e}")
        # 如果PyMuPDF失败，使用备用方案解析XML并转换为图片
        return ofd_to_images_fallback(file_path, output_dir)

def ofd_to_images_fallback(file_path, output_dir=None):
    """备用方案：解析XML并将OFD转换为图片"""
    if not output_dir:
        output_dir = file_path.replace('.ofd', '_images')

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 解析OFD文件获取基本信息
        data_dict = parse_ofd(file_path)
        text_objects = data_dict['text_objects']

        # 获取页面尺寸（从OFD文件中提取或使用A4默认值）
        page_width, page_height = A4  # 默认A4尺寸

        # 尝试从OFD文件中获取实际页面尺寸
        try:
            unzip_path = data_dict.get('unzip_path')
            if unzip_path:
                # 查找页面尺寸信息
                for root, dirs, files in os.walk(unzip_path):
                    for file in files:
                        if file.endswith('.xml'):
                            xml_path = os.path.join(root, file)
                            with open(xml_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if 'PhysicalBox' in content:
                                    # 尝试提取页面尺寸
                                    import re
                                    box_match = re.search(r'PhysicalBox[^>]*>([^<]+)', content)
                                    if box_match:
                                        box_values = box_match.group(1).strip().split()
                                        if len(box_values) >= 4:
                                            page_width = float(box_values[2]) * 2.83465  # 转换为像素
                                            page_height = float(box_values[3]) * 2.83465
                                            break
        except Exception as e:
            print(f"无法获取页面尺寸，使用默认A4: {e}")

        print(f"页面尺寸: {page_width} x {page_height}")

        # 创建图片
        image = Image.new('RGB', (int(page_width), int(page_height)), 'white')
        draw = ImageDraw.Draw(image)

        # 尝试加载中文字体
        try:
            font = ImageFont.truetype('simsun.ttc', 12)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype('arial.ttf', 12)
            except (OSError, IOError):
                font = ImageFont.load_default()

        # 绘制文本对象
        for i, obj in enumerate(text_objects):
            # 获取文本内容
            text_code = obj.get('ofd:TextCode', {})
            if isinstance(text_code, list):
                text_code = text_code[0] if text_code else {}

            text_content = text_code.get('#text', '')
            if not text_content:
                continue

            # 获取位置信息
            x_attr = text_code.get('@X', '0')
            y_attr = text_code.get('@Y', '0')

            try:
                x = float(x_attr)
                y = float(y_attr)
            except (ValueError, TypeError):
                x = 0
                y = 0

            # 获取字体大小
            size_attr = obj.get('@Size', '12')
            try:
                font_size = int(float(size_attr))
                # 尝试加载对应大小的字体
                try:
                    font = ImageFont.truetype('simsun.ttc', font_size)
                except (OSError, IOError):
                    font = ImageFont.load_default()
            except (ValueError, TypeError):
                font_size = 12

            # 绘制文本
            try:
                draw.text((x, y), text_content, fill='black', font=font)
            except Exception as e:
                print(f"绘制文本失败: {e}, 内容: {text_content[:50]}...")
                # 使用默认字体重试
                draw.text((x, y), text_content, fill='black')

        # 保存图片
        image_path = os.path.join(output_dir, 'page_001.png')
        image.save(image_path)

        print(f"图片已生成: {image_path}")
        print(f"共处理了 {len(text_objects)} 个文本对象")

        return [image_path]

    except Exception as e:
        print(f"备用方案失败: {e}")
        raise e

# 示例调用

# 本地OFD文件路径
ofd_file_path = r"C:\Users\CHENQIMING\Desktop\工作数据\测试文件\特殊格式文章\弘扬优良传统测试副本.ofd"

# 解析OFD文件
print("正在解析OFD文件...")
data_dict = parse_ofd(ofd_file_path)
print("解析完成，获取到的数据:")
print(data_dict)

# 开始转换
print("\n" + "="*50)
print("开始OFD文件转换...")
print("="*50)

# 转换为PDF（推荐）
print("\n正在尝试转换为PDF...")
try:
    result = ofd_to_pdf(ofd_file_path)
    if isinstance(result, list):
        print(f"图片转换完成，共生成 {len(result)} 张图片")
        for path in result[:3]:
            print(f"  {path}")
    else:
        print(f"PDF转换完成: {result}")
except Exception as e:
    print(f"转换失败: {e}")

print("\n" + "="*50)
print("转换过程完成！")
print("="*50)