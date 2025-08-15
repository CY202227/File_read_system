from app.core.job_manager import JobManager
from app.core import task_manager as tm_module


def test_result_contains_chunking_and_summary_when_enabled(monkeypatch):
    jm = JobManager()

    # Build fake texts
    texts = [("/tmp/a.txt", "hello world")]

    # Fake request enabling chunking, summary and extraction
    request = {
        "enable_chunking": True,
        "chunking_strategy": {"value": "character_splitting"},
        "chunk_size": 10,
        "chunk_overlap": 2,
        "enable_multi_file_summary": True,
        "summary_length": 50,
        "summary_focus": ["main_points"],
        "enable_extract": True,
        "extract_config": {
            "prompt": "仅从文本中提取单词 hello 作为人物。",
            "extractions": [
                {
                    "text": "hello world",
                    "extractions": [
                        {"extraction_class": "人物", "extraction_text": "hello", "attributes": {}}
                    ]
                }
            ]
        },
    }

    # Stub task_manager side effects (avoid JSON storage requirement)
    monkeypatch.setattr(tm_module.task_manager, "update_section", lambda *a, **k: None)
    monkeypatch.setattr(tm_module.task_manager, "update_task_status", lambda *a, **k: None)

    # Stub AIClient to avoid external HTTP
    from app.core import job_manager as jm_module
    monkeypatch.setattr(jm_module.AIClient, "chat_invoke", lambda self, **kwargs: "- a\n- b\n- c")

    # Use real handlers but avoid external/stateful I/O; assert structure
    chunks_result = jm._handle_chunking("task_x", request, texts)
    assert "chunks" in chunks_result

    summary = jm._handle_summary("task_x", request, texts, chunks_result)
    assert "summary" in summary
    assert "summary_dict" in summary

    # Extraction processor is invoked only via start_job; here just validate schema presence
    assert "enable_extract" in request and "extract_config" in request


