#!/usr/bin/env python3
"""Knowledge MCP 冒烟：直接调三工具（无需先起 HTTP 进程）。

用法:
  uv run python scripts/smoke_knowledge_mcp.py
  uv run python scripts/smoke_knowledge_mcp.py --query 差旅报销
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from ka_knowledge_mcp.service import (  # noqa: E402
    get_document_section,
    hybrid_search,
    list_sources,
)


async def run(query: str, top_k: int) -> int:
    sources = list_sources()
    print(f"[list_sources] count={len(sources)}")
    for s in sources:
        print(f"  - {s.get('filename') or s['title']} ({s['domain']}) id={s['doc_id'][:8]}...")

    if len(sources) < 5:
        print(f"[FAIL] 入库文档不足 5 篇，当前 {len(sources)}。请先: uv run python scripts/ingest_docs.py")
        return 1

    hits = await hybrid_search(query, top_k=top_k)
    print(f"\n[hybrid_search] query={query!r} count={len(hits)}")
    if not hits:
        print("[FAIL] 检索无结果")
        return 1

    required = {"doc_id", "title", "section", "score"}
    for i, h in enumerate(hits, 1):
        missing = required - set(h.keys())
        if missing:
            print(f"[FAIL] hit#{i} 缺少字段: {missing}")
            return 1
        print(
            f"  #{i} score={h['score']:.4f} title={h['title']} "
            f"section={h.get('section')} file={h.get('filename')}"
        )
        print(f"       snippet={h.get('snippet', '')[:120]}")

    top = hits[0]
    section = get_document_section(top["doc_id"], top.get("section"))
    print(f"\n[get_document_section] found={section.get('found')} title={section.get('title')}")
    if not section.get("found"):
        print(json.dumps(section, ensure_ascii=False, indent=2))
        print("[FAIL] get_document_section 未找到")
        return 1
    print(f"  content_preview={str(section.get('content', ''))[:200]}...")

    print("\nSMOKE OK: hybrid_search / get_document_section / list_sources")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="差旅报销")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    return asyncio.run(run(args.query, args.top_k))


if __name__ == "__main__":
    raise SystemExit(main())
