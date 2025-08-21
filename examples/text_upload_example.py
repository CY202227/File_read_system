"""
纯文本上传功能示例
Text upload functionality example
"""

import requests
import json


def test_text_upload():
    """测试纯文本上传功能"""
    
    # API基础URL
    base_url = "http://localhost:5015/api/v1/api"
    
    # 测试用例1: HTML内容，自动检测
    print("=== 测试用例1: HTML内容，自动检测 ===")
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>测试页面</title>
    </head>
    <body>
        <h1>这是一个测试页面</h1>
        <p>这是段落内容。</p>
        <a href="https://example.com">链接</a>
    </body>
    </html>
    """
    
    response = requests.post(
        f"{base_url}/upload/text",
        json={
            "content": html_content,
            "auto_detect": True
        }
    )
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"任务ID: {result['task_id']}")
        print(f"文件名: {result['files'][0]['original_filename']}")
        print(f"文件大小: {result['files'][0]['file_size']} bytes")
    else:
        print(f"错误: {response.text}")
    
    print("\n" + "="*50 + "\n")
    
    # 测试用例2: Markdown内容，自动检测
    print("=== 测试用例2: Markdown内容，自动检测 ===")
    md_content = """
    # 测试文档
    
    ## 章节1
    
    这是一个**粗体**文本，这是*斜体*文本。
    
    ### 列表
    - 项目1
    - 项目2
    - 项目3
    
    ### 代码
    ```python
    print("Hello, World!")
    ```
    
    [链接文本](https://example.com)
    """
    
    response = requests.post(
        f"{base_url}/upload/text",
        json={
            "content": md_content,
            "auto_detect": True
        }
    )
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"任务ID: {result['task_id']}")
        print(f"文件名: {result['files'][0]['original_filename']}")
        print(f"文件大小: {result['files'][0]['file_size']} bytes")
    else:
        print(f"错误: {response.text}")
    
    print("\n" + "="*50 + "\n")
    
    # 测试用例3: 纯文本内容，自动检测
    print("=== 测试用例3: 纯文本内容，自动检测 ===")
    plain_text = """
    这是一个纯文本文件。
    
    包含多行内容。
    没有任何特殊格式。
    
    只是普通的文本内容。
    """
    
    response = requests.post(
        f"{base_url}/upload/text",
        json={
            "content": plain_text,
            "auto_detect": True
        }
    )
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"任务ID: {result['task_id']}")
        print(f"文件名: {result['files'][0]['original_filename']}")
        print(f"文件大小: {result['files'][0]['file_size']} bytes")
    else:
        print(f"错误: {response.text}")
    
    print("\n" + "="*50 + "\n")
    
    # 测试用例4: 指定格式（手动模式）
    print("=== 测试用例4: 指定格式（手动模式） ===")
    custom_content = """
    这是自定义内容。
    即使看起来像Markdown，也会使用指定的扩展名。
    """
    
    response = requests.post(
        f"{base_url}/upload/text",
        json={
            "content": custom_content,
            "auto_detect": False,
            "extension": "txt"
        }
    )
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"任务ID: {result['task_id']}")
        print(f"文件名: {result['files'][0]['original_filename']}")
        print(f"文件大小: {result['files'][0]['file_size']} bytes")
    else:
        print(f"错误: {response.text}")
    
    print("\n" + "="*50 + "\n")
    
    # 测试用例5: 手动模式指定HTML扩展名
    print("=== 测试用例5: 手动模式指定HTML扩展名 ===")
    html_content_manual = """
    <div>这是HTML内容</div>
    <p>段落内容</p>
    """
    
    response = requests.post(
        f"{base_url}/upload/text",
        json={
            "content": html_content_manual,
            "auto_detect": False,
            "extension": "html"
        }
    )
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"任务ID: {result['task_id']}")
        print(f"文件名: {result['files'][0]['original_filename']}")
        print(f"文件大小: {result['files'][0]['file_size']} bytes")
    else:
        print(f"错误: {response.text}")
    
    print("\n" + "="*50 + "\n")
    
    # 测试用例6: 使用你提供的JSON格式
    print("=== 测试用例6: 使用你提供的JSON格式 ===")
    test_content = "# 标题\n这是一个 Markdown 文档\n- 列表项1\n- 列表项2"
    
    response = requests.post(
        f"{base_url}/upload/text",
        json={
            "content": test_content,
            "priority": "3", 
            "auto_detect": True
        }
    )
    
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"任务ID: {result['task_id']}")
        print(f"文件名: {result['files'][0]['original_filename']}")
        print(f"文件大小: {result['files'][0]['file_size']} bytes")
    else:
        print(f"错误: {response.text}")


if __name__ == "__main__":
    test_text_upload()
