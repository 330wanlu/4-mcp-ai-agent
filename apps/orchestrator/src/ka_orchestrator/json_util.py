"""从 LLM 文本中稳健提取 JSON。"""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """优先整段解析；失败则取首个 {...} 块。"""
    text = (text or "").strip()
    if not text:
        raise ValueError("empty LLM response")

    # 去掉常见 markdown 围栏
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            return data
    raise ValueError(f"无法解析 JSON: {text[:200]}")
