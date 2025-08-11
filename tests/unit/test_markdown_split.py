from app.vectorization.chunking import level3_document_specific_splitting, ChunkingConfig


def test_markdown_heading_and_code_blocks_grouping():
    md = """# Title

text

```python
print('hi')
```

## Sub
list:
- a
- b
"""
    chunks = level3_document_specific_splitting(
        md,
        document_type="markdown",
        config=ChunkingConfig(chunk_size=1000, chunk_overlap=50),
        doc_options={
            "preserve_headers": True,
            "preserve_code_blocks": True,
            "preserve_lists": True,
        },
    )
    assert any("```python" in c for c in chunks)
    assert any(c.lstrip().startswith("# ") for c in chunks)


