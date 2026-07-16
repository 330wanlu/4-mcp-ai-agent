"""阶段 2 Demo CLI：问题 → Agent Graph → 答案 + citations + agent_trace。

用法:
  uv run python scripts/demo_cli.py
  uv run python scripts/demo_cli.py --question "试用期员工年假怎么算？"
  uv run python scripts/demo_cli.py --golden --limit 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(text.encode(enc, errors="replace").decode(enc, errors="replace"))


def _load_golden_questions(limit: int | None = None) -> list[dict]:
    data = json.loads(
        (ROOT / "data" / "golden_set" / "golden_set.json").read_text(encoding="utf-8")
    )
    items = data["qa"]
    if limit is not None:
        items = items[:limit]
    return items


def _citation_filenames(citations: list[dict]) -> set[str]:
    names: set[str] = set()
    for c in citations:
        fn = c.get("filename")
        if fn:
            names.add(str(fn))
        title = c.get("title") or ""
        if title.endswith(".md"):
            names.add(title)
        sp = c.get("source_path") or ""
        if sp:
            names.add(Path(sp).name)
    return names


def _has_reasonable_citation(citations: list[dict], source_docs: list[str]) -> bool:
    if not citations or not source_docs:
        return False
    found = _citation_filenames(citations)
    # 也用 title 子串兜底（title 常为去扩展名的制度名）
    titles = " ".join(str(c.get("title") or "") for c in citations)
    for doc in source_docs:
        stem = Path(doc).stem
        if doc in found or stem in found:
            return True
        if stem and stem in titles:
            return True
    return False


async def _run_one(question: str, *, session_id: str | None = None) -> dict:
    from ka_orchestrator.pipeline import run_qa_pipeline
    from ka_orchestrator.redis_state import SessionStore

    store = SessionStore()
    try:
        result = await run_qa_pipeline(
            question, session_id=session_id, store=store, persist=True
        )
        return result
    finally:
        await store.close()


def _print_result(result: dict) -> None:
    _safe_print("=" * 60)
    _safe_print(f"session_id: {result.get('session_id')}")
    _safe_print(f"intent:     {result.get('intent')}")
    _safe_print(f"question:   {result.get('question')}")
    _safe_print("-" * 60)
    _safe_print("answer:")
    _safe_print(str(result.get("answer") or ""))
    _safe_print("-" * 60)
    _safe_print("citations:")
    for i, c in enumerate(result.get("citations") or [], 1):
        _safe_print(
            f"  [{i}] {c.get('filename') or c.get('title')} | "
            f"section={c.get('section')} | score={c.get('score')}"
        )
    _safe_print("-" * 60)
    _safe_print("agent_trace:")
    for step in result.get("agent_trace") or []:
        _safe_print(f"  - {step.get('agent')}: {step.get('action')} {step.get('detail')}")
    if result.get("note"):
        _safe_print(f"note: {result['note']}")


async def main_async(args: argparse.Namespace) -> int:
    if args.golden:
        items = _load_golden_questions(args.limit)
        ok = 0
        for item in items:
            qid = item["id"]
            question = item["question"]
            _safe_print(f"\n>>> {qid}: {question}")
            result = await _run_one(question)
            _print_result(result)
            hit = _has_reasonable_citation(
                result.get("citations") or [], item.get("source_docs") or []
            )
            if hit:
                ok += 1
                _safe_print(f"[citation] OK vs {item['source_docs']}")
            else:
                _safe_print(f"[citation] MISS expected={item['source_docs']}")
        _safe_print(f"\n=== golden citation hit: {ok}/{len(items)} ===")
        return 0 if ok >= max(1, int(len(items) * 0.7)) else 1

    question = args.question or "试用期员工年假怎么算？能不能请？"
    result = await _run_one(question)
    _print_result(result)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="阶段 2 Agent 问答 Demo CLI")
    parser.add_argument("--question", "-q", type=str, default=None)
    parser.add_argument("--golden", action="store_true", help="跑黄金集问答")
    parser.add_argument("--limit", type=int, default=None, help="黄金集条数上限")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
