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
    # After size/overlap normalization, at least the delimiter must produce >1 segments
    assert len(chunks) >= 2
    # Ensure delimiter kept at boundaries for non-last segments
    assert any(seg.endswith("——END——") for seg in chunks[:-1])


