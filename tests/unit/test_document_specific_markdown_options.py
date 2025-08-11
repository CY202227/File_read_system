from app.vectorization.chunking import level3_document_specific_splitting, ChunkingConfig


def test_markdown_without_heading_grouping():
    md = """# T\npara\n\n- a\n- b\n"""
    chunks = level3_document_specific_splitting(
        md,
        document_type="markdown",
        config=ChunkingConfig(chunk_size=1000, chunk_overlap=50),
        doc_options={
            "preserve_headers": False,
            "preserve_code_blocks": True,
            "preserve_lists": True,
        },
    )
    # With no heading grouping, the first chunk should not necessarily start with heading
    assert any("- a" in c for c in chunks)


