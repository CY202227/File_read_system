from __future__ import annotations

from typing import Any, Dict, List

import langextract as lx
from config.settings import settings


def extract_information(text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """基于 LangExtract 执行信息抽取。

    Args:
        text: 待抽取的整段文本（建议已完成预处理/合并）。
        config: 必填配置，形如：
            {
              "prompt": str,
              "extractions": [
                  {"text": str, "extractions": [
                      {"extraction_class": str, "extraction_text": str, "attributes": {...}}
                  ]}
              ]
            }

    Returns:
        dict: {"document_id", "text_length", "extractions": [...]}，可直接写入 result_data["extraction"]。
    """
    prompt = (config or {}).get("prompt")
    examples_cfg = (config or {}).get("extractions") or []
    if not prompt or not isinstance(examples_cfg, list):
        raise ValueError("config.prompt 与 config.extractions 为必填")

    lx_examples: List[lx.data.ExampleData] = []
    for ex in examples_cfg:
        items = []
        for it in (ex.get("extractions") or []):
            items.append(
                lx.data.Extraction(
                    extraction_class=str(it.get("extraction_class", "")).strip(),
                    extraction_text=str(it.get("extraction_text", "")).strip(),
                    attributes=dict(it.get("attributes") or {}),
                )
            )
        lx_examples.append(
            lx.data.ExampleData(
                text=str(ex.get("text", "")),
                extractions=items,
            )
        )

    if not text or not text.strip():
        return {"document_id": None, "text_length": 0, "extractions": []}

    result = lx.extract(
        text_or_documents=text,
        prompt_description=str(prompt),
        examples=lx_examples,
        language_model_type=lx.inference.OpenAILanguageModel,
        model_id=settings.QWEN3_MODEL_NAME or "Qwen3",
        language_model_params={
            "base_url": settings.QWEN3_BASE_URL or None,
        },
        format_type=lx.data.FormatType.JSON,
        temperature=0.0,
        max_char_buffer=15000,
        fence_output=False,
        use_schema_constraints=False,
        api_key=settings.QWEN3_API_KEY or None,
    )

    doc = result if isinstance(result, lx.data.AnnotatedDocument) else next(iter(result), None)
    if doc is None:
        return {"document_id": None, "text_length": 0, "extractions": []}

    def _extract_to_dict(e: lx.data.Extraction) -> Dict[str, Any]:
        return {
            "extraction_class": e.extraction_class,
            "extraction_text": e.extraction_text,
            "char_interval": (
                None
                if e.char_interval is None
                else {"start_pos": e.char_interval.start_pos, "end_pos": e.char_interval.end_pos}
            ),
            "alignment_status": None if e.alignment_status is None else e.alignment_status.value,
            "extraction_index": e.extraction_index,
            "group_index": e.group_index,
            "description": e.description,
            "attributes": e.attributes,
        }

    return {
        "document_id": doc.document_id,
        "text_length": len(doc.text or ""),
        "extractions": [_extract_to_dict(e) for e in (doc.extractions or [])],
    }


