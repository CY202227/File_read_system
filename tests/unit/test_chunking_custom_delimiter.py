from app.vectorization.chunking import chunk_text


def test_custom_delimiter_splitting_basic():
    text = "A——END——B——END——C"
    result = chunk_text(
        text=text,
        enable_chunking=True,
        chunking_strategy_value="custom_delimiter_splitting",
        chunk_size=100,
        chunk_overlap=10,
        chunking_config={
            "custom_delimiter_config": {"delimiter": "——END——"}
        },
        ai_client=None,
    )
    chunks = result.get("chunks", [])
    # 现在应该产生3个块：["A", "B", "C"]，分隔符被移除
    assert len(chunks) == 3
    assert chunks[0] == "A"
    assert chunks[1] == "B"
    assert chunks[2] == "C"


def test_custom_delimiter_splitting_markdown_headers():
    """测试使用自定义分隔符按markdown标题分块"""
    text = """# 标题1
这是第一个标题下的内容。

## 标题2
这是第二个标题下的内容。

### 标题3
这是第三个标题下的内容。"""
    
    result = chunk_text(
        text=text,
        enable_chunking=True,
        chunking_strategy_value="custom_delimiter_splitting",
        chunk_size=100,
        chunk_overlap=10,
        chunking_config={
            "custom_delimiter_config": {"delimiter": "# "}
        },
        ai_client=None,
    )
    chunks = result.get("chunks", [])
    
    # 应该产生4个块：["", "标题1\n这是第一个标题下的内容。\n\n", "标题2\n这是第二个标题下的内容。\n\n", "标题3\n这是第三个标题下的内容。"]
    assert len(chunks) == 4
    # 第一个块应该为空（在第一个标题之前）
    assert chunks[0] == ""
    # 其他块应该包含标题和内容，但不包含分隔符
    assert chunks[1] == "标题1\n这是第一个标题下的内容。\n\n#"
    assert chunks[2] == "标题2\n这是第二个标题下的内容。\n\n##"
    assert chunks[3] == "标题3\n这是第三个标题下的内容。"


def test_custom_delimiter_splitting_double_newlines():
    """测试使用双换行符作为分隔符进行分块"""
    text = """# 2025年7月份工业生产者出厂价格环比降幅收窄

　　2025年7月份，全国工业生产者出厂价格环比下降0.2%。

![](data:image/png;base64...)

**一、工业生产者价格同比变动情况**

　　7月份，工业生产者出厂价格中，生产资料价格下降4.3%。

![](data:image/png;base64...)

**二、工业生产者价格环比变动情况**

　　7月份，工业生产者出厂价格中，生产资料价格下降0.2%。"""
    
    result = chunk_text(
        text=text,
        enable_chunking=True,
        chunking_strategy_value="custom_delimiter_splitting",
        chunk_size=999999,
        chunk_overlap=0,
        chunking_config={
            "custom_delimiter_config": {"delimiter": "\n\n"}
        },
        ai_client=None,
    )
    chunks = result.get("chunks", [])
    
    # 应该产生多个块，每两个换行符之间为一个块
    assert len(chunks) > 1
    # 第一个块应该包含标题
    assert "# 2025年7月份工业生产者出厂价格环比降幅收窄" in chunks[0]
    # 应该包含内容块
    assert any("工业生产者出厂价格环比下降0.2%" in chunk for chunk in chunks)
    assert any("工业生产者价格同比变动情况" in chunk for chunk in chunks)
    assert any("工业生产者价格环比变动情况" in chunk for chunk in chunks)


def test_custom_delimiter_splitting_empty_delimiter():
    """测试空分隔符的情况"""
    text = "这是一个测试文本"
    
    result = chunk_text(
        text=text,
        enable_chunking=True,
        chunking_strategy_value="custom_delimiter_splitting",
        chunk_size=100,
        chunk_overlap=10,
        chunking_config={
            "custom_delimiter_config": {"delimiter": ""}
        },
        ai_client=None,
    )
    chunks = result.get("chunks", [])
    
    # 空分隔符应该返回整个文本作为一个块
    assert len(chunks) == 1
    assert chunks[0] == text
