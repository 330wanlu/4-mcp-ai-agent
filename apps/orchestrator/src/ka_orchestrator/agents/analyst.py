"""Analyst Agent：基于检索结果生成带引用答案。"""

from __future__ import annotations

import json
from typing import Any

from ka_common.schema import Citation
from ka_llm import ChatMessage, ChatProvider


def _format_materials(hits: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for i, h in enumerate(hits, 1):
        lines.append(
            f"[{i}] title={h.get('title')} | section={h.get('section')} | "
            f"filename={h.get('filename')} | score={h.get('score')}\n"
            f"snippet: {h.get('snippet')}"
        )
    return "\n\n".join(lines) if lines else "(无检索结果)"


ANALYST_SYSTEM = """你是企业制度 Analyst。
仅依据「参考资料」回答用户问题，不要编造制度外内容。
若资料不足，明确说明不足并给出可核对的文档名。
回答要求：
1. 用简洁中文直接回答要点
2. 关键数字、时限、金额、审批角色必须来自资料
3. 在答案末尾用「引用：」列出用到的资料序号，如 引用：[1][3]
不要输出 JSON，只输出自然语言答案。
"""


async def run_analyst(
    question: str,
    *,
    intent: str,
    hits: list[dict[str, Any]],
    provider: ChatProvider,
    memory_context: str | None = None,
) -> dict[str, Any]:
    materials = _format_materials(hits)
    mem = (memory_context or "").strip()
    mem_block = f"\n会话/偏好记忆:\n{mem}\n" if mem else ""
    user = (
        f"意图: {intent}\n"
        f"用户问题: {question}\n"
        f"{mem_block}\n"
        f"参考资料:\n{materials}"
    )
    answer = await provider.chat(
        [
            ChatMessage(role="system", content=ANALYST_SYSTEM),
            ChatMessage(role="user", content=user),
        ],
        temperature=0.2,
        max_tokens=2048,
        thinking=False,
    )

    citations = [
        Citation(
            doc_id=str(h.get("doc_id") or ""),
            title=str(h.get("title") or ""),
            section=h.get("section"),
            score=h.get("score"),
            snippet=h.get("snippet"),
        ).model_dump()
        for h in hits
        if h.get("doc_id")
    ]
    # 附带 filename 便于黄金集对齐
    for c, h in zip(citations, hits):
        if h.get("filename"):
            c["filename"] = h["filename"]
        if h.get("source_path"):
            c["source_path"] = h["source_path"]

    return {
        "answer": answer,
        "citations": citations,
        "materials_used": len(hits),
        "debug_materials": json.loads(json.dumps(hits, ensure_ascii=False)),
    }
