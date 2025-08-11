from app.vectorization.chunking import chunk_text


def test_level1_character_windowing():
    text = "abcdefghij"  # 10 chars
    res = chunk_text(
        text=text,
        enable_chunking=True,
        chunking_strategy_value="character_splitting",
        chunk_size=4,
        chunk_overlap=1,
        chunking_config={},
        ai_client=None,
    )
    chunks = res.get("chunks", [])
    # Expect roughly ceil(10/3)=4 chunks with overlap accounted for
    assert len(chunks) >= 3
    assert all(isinstance(c, str) and len(c) > 0 for c in chunks)


def test_level2_recursive_with_custom_separators():
    text = "para1. para2\npara3\n\npara4"
    res = chunk_text(
        text=text,
        enable_chunking=True,
        chunking_strategy_value="recursive_character_splitting",
        chunk_size=50,
        chunk_overlap=5,
        chunking_config={
            "recursive_splitting_config": {
                "separators": ["\n\n", "\n", ". ", " "]
            }
        },
        ai_client=None,
    )
    chunks = res.get("chunks", [])
    # Depending on normalization, at least one chunk should contain later paragraphs
    assert len(chunks) >= 1
    assert any("para3" in c or "para4" in c for c in chunks)


