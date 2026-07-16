"""阶段 2/4 Demo CLI：问答 + 行动闸门。

用法:
  uv run python scripts/demo_cli.py
  uv run python scripts/demo_cli.py --question "试用期员工年假怎么算？"
  uv run python scripts/demo_cli.py --golden --limit 10
  uv run python scripts/demo_cli.py --action
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


def _load_golden_actions(limit: int | None = None) -> list[dict]:
    data = json.loads(
        (ROOT / "data" / "golden_set" / "golden_set.json").read_text(encoding="utf-8")
    )
    items = data["actions"]
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
        return await run_qa_pipeline(
            question, session_id=session_id, store=store, persist=True
        )
    finally:
        await store.close()


def _print_result(result: dict) -> None:
    _safe_print("=" * 60)
    _safe_print(f"session_id: {result.get('session_id')}")
    _safe_print(f"intent:     {result.get('intent')}")
    _safe_print(f"status:     {result.get('status')}")
    _safe_print(f"question:   {result.get('question')}")
    _safe_print("-" * 60)
    _safe_print("answer:")
    _safe_print(str(result.get("answer") or ""))
    if result.get("action_plan"):
        plan = result["action_plan"]
        _safe_print("-" * 60)
        _safe_print(
            f"action_plan: type={plan.get('action_type')} title={plan.get('title')}"
        )
        _safe_print(f"  tickets={len(plan.get('tickets') or [])}")
    if result.get("pending_action"):
        _safe_print(f"pending_action: {result['pending_action'].get('action_id')}")
    if result.get("guard"):
        _safe_print(f"guard: {result['guard']}")
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


async def _run_actions(limit: int | None) -> int:
    from ka_business_mcp.service import count_tickets
    from ka_orchestrator.confirmation import confirm_pending_action
    from ka_orchestrator.redis_state import SessionStore

    items = _load_golden_actions(limit)
    type_ok = 0
    gate_ok = 0

    for item in items:
        aid = item["id"]
        task = item["task"]
        expected = item["expected_action_type"]
        _safe_print(f"\n>>> {aid}: {task}")
        result = await _run_one(task)
        _print_result(result)

        plan = result.get("action_plan") or {}
        got = plan.get("action_type")
        if got == expected:
            type_ok += 1
            _safe_print(f"[action_type] OK {got}")
        else:
            _safe_print(f"[action_type] MISS expected={expected} got={got}")

        sid = result["session_id"]
        before = count_tickets(session_id=sid)
        if expected == "refuse_or_require_travel_order":
            if result.get("status") == "blocked" and before == 0:
                gate_ok += 1
                _safe_print("[gate] OK blocked, no tickets")
            else:
                _safe_print(
                    f"[gate] FAIL refuse case status={result.get('status')} tickets={before}"
                )
            continue

        # 可确认行动：确认前无单，确认后有单
        if result.get("status") != "awaiting_confirmation":
            _safe_print(f"[gate] SKIP/FAIL not awaiting (status={result.get('status')})")
            continue
        if before != 0:
            _safe_print(f"[gate] FAIL tickets exist before confirm: {before}")
            continue

        store = SessionStore()
        try:
            confirmed = await confirm_pending_action(sid, store=store)
        finally:
            await store.close()
        after = count_tickets(session_id=sid)
        if confirmed.get("ok") and after > 0:
            gate_ok += 1
            _safe_print(f"[gate] OK confirm created tickets={after}")
        else:
            _safe_print(f"[gate] FAIL confirm={confirmed} tickets={after}")

    _safe_print(f"\n=== action_type hit: {type_ok}/{len(items)} (need >=3) ===")
    _safe_print(f"=== gate checks ok: {gate_ok}/{len(items)} ===")
    return 0 if type_ok >= 3 else 1


async def main_async(args: argparse.Namespace) -> int:
    if args.action:
        return await _run_actions(args.limit)

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
    parser = argparse.ArgumentParser(description="Agent 问答/行动 Demo CLI")
    parser.add_argument("--question", "-q", type=str, default=None)
    parser.add_argument("--golden", action="store_true", help="跑黄金集问答")
    parser.add_argument("--action", action="store_true", help="跑黄金行动+确认闸门")
    parser.add_argument("--limit", type=int, default=None, help="条数上限")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
