"""阶段 5 评测：黄金集引用命中 / 行动成功率 / Guard 拒答与拦截。

用法:
  uv run python scripts/run_eval.py
  uv run python scripts/run_eval.py --limit 3
  uv run python scripts/run_eval.py --skip-actions
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

REPORT_DIR = ROOT / "data" / "eval_reports"
DOCS_REPORT = ROOT / "docs" / "eval-report.md"


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(text.encode(enc, errors="replace").decode(enc, errors="replace"))


def _load_golden() -> dict[str, Any]:
    return json.loads(
        (ROOT / "data" / "golden_set" / "golden_set.json").read_text(encoding="utf-8")
    )


def _citation_hit(citations: list[dict], source_docs: list[str]) -> bool:
    if not citations or not source_docs:
        return False
    found: set[str] = set()
    titles = ""
    for c in citations:
        fn = c.get("filename")
        if fn:
            found.add(str(fn))
        title = str(c.get("title") or "")
        titles += " " + title
        if title.endswith(".md"):
            found.add(title)
        sp = c.get("source_path") or ""
        if sp:
            found.add(Path(str(sp)).name)
    for doc in source_docs:
        stem = Path(doc).stem
        if doc in found or stem in found:
            return True
        if stem and stem in titles:
            return True
    return False


async def _run_pipeline(question: str, *, user_id: str = "eval-user") -> dict[str, Any]:
    from ka_orchestrator.pipeline import run_qa_pipeline
    from ka_orchestrator.redis_state import SessionStore

    store = SessionStore()
    try:
        return await run_qa_pipeline(
            question,
            user_id=user_id,
            store=store,
            persist=True,
        )
    finally:
        await store.close()


async def eval_qa(items: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    citation_ok = 0
    degraded = 0
    for item in items:
        qid = item["id"]
        _safe_print(f"\n[QA] {qid}: {item['question']}")
        result = await _run_pipeline(item["question"])
        hit = _citation_hit(
            result.get("citations") or [], item.get("source_docs") or []
        )
        status = result.get("status")
        if hit:
            citation_ok += 1
        if status == "degraded":
            degraded += 1
        _safe_print(
            f"  status={status} citation={'OK' if hit else 'MISS'} "
            f"guard={(result.get('guard') or {}).get('decision')}"
        )
        rows.append(
            {
                "id": qid,
                "status": status,
                "citation_hit": hit,
                "citation_count": len(result.get("citations") or []),
                "guard": (result.get("guard") or {}).get("decision"),
            }
        )
    total = len(items) or 1
    return {
        "total": len(items),
        "citation_hits": citation_ok,
        "citation_rate": round(citation_ok / total, 4),
        "degraded": degraded,
        "degrade_rate": round(degraded / total, 4),
        "rows": rows,
        "pass": citation_ok >= max(1, int(len(items) * 0.7)),
    }


async def eval_actions(items: list[dict[str, Any]]) -> dict[str, Any]:
    from ka_business_mcp.service import count_tickets
    from ka_orchestrator.confirmation import confirm_pending_action
    from ka_orchestrator.redis_state import SessionStore

    rows: list[dict[str, Any]] = []
    type_ok = 0
    gate_ok = 0
    for item in items:
        aid = item["id"]
        expected = item["expected_action_type"]
        _safe_print(f"\n[ACT] {aid}: {item['task']}")
        result = await _run_pipeline(item["task"])
        got = (result.get("action_plan") or {}).get("action_type")
        type_match = got == expected
        if type_match:
            type_ok += 1

        sid = result["session_id"]
        before = count_tickets(session_id=sid)
        gate_pass = False
        if expected == "refuse_or_require_travel_order":
            gate_pass = result.get("status") == "blocked" and before == 0
        elif result.get("status") == "awaiting_confirmation" and before == 0:
            store = SessionStore()
            try:
                confirmed = await confirm_pending_action(sid, store=store)
            finally:
                await store.close()
            after = count_tickets(session_id=sid)
            gate_pass = bool(confirmed.get("ok") and after > 0)

        if gate_pass:
            gate_ok += 1
        _safe_print(
            f"  type={'OK' if type_match else 'MISS'} expected={expected} got={got} "
            f"gate={'OK' if gate_pass else 'FAIL'} status={result.get('status')}"
        )
        rows.append(
            {
                "id": aid,
                "expected": expected,
                "got": got,
                "type_match": type_match,
                "gate_pass": gate_pass,
                "status": result.get("status"),
            }
        )
    total = len(items) or 1
    return {
        "total": len(items),
        "type_hits": type_ok,
        "type_rate": round(type_ok / total, 4),
        "gate_hits": gate_ok,
        "gate_rate": round(gate_ok / total, 4),
        "rows": rows,
        "pass": type_ok >= 3 and gate_ok >= 3,
    }


async def eval_guardrails() -> dict[str, Any]:
    """无引用降级 + 行动冲突拦截（确定性场景）。"""
    from ka_orchestrator.agents.guard import run_answer_guard, run_guard

    # 1) 无引用 → 降级
    ag = run_answer_guard(
        question="今天中午吃什么？",
        answer="随便吃点吧",
        citations=[],
        hits=[],
        intent="qa",
    )
    no_cite_ok = ag.get("decision") == "degraded" and not ag.get("allowed")

    # 2) 行动冲突
    blocked = run_guard(
        "帮我直接创建一个报销上周自行购买机票的报销单草稿（没有出差申请）。",
        {
            "action_type": "refuse_or_require_travel_order",
            "tickets": [
                {
                    "ticket_type": "reimbursement",
                    "payload": {},
                }
            ],
        },
    )
    action_block_ok = blocked.get("decision") == "blocked" and not blocked.get("allowed")

    # 3) Memory 读写
    from ka_memory_mcp.service import (
        get_session_summary,
        get_user_preference,
        upsert_session_summary,
        upsert_user_preference,
    )

    sid = f"eval-mem-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    uid = "eval-user"
    upsert_session_summary(sid, summary="评测会话摘要", user_id=uid)
    upsert_user_preference(uid, preferences={"locale": "zh-CN", "last_domain": "travel"})
    mem_ok = bool(get_session_summary(sid).get("found")) and bool(
        get_user_preference(uid).get("found")
    )

    # 4) 流水线：域外闲聊应降级
    result = await _run_pipeline("写一首关于比特币的诗", user_id=uid)

    checks = {
        "answer_guard_no_citation": no_cite_ok,
        "action_guard_block": action_block_ok,
        "memory_upsert_get": mem_ok,
        "pipeline_out_of_domain_degrade": result.get("status") == "degraded",
    }

    passed = all(checks.values())
    _safe_print("\n[Guardrails]")
    for k, v in checks.items():
        _safe_print(f"  {k}: {'OK' if v else 'FAIL'}")
    return {"checks": checks, "pass": passed, "out_of_domain_status": result.get("status")}


def _render_report(report: dict[str, Any]) -> str:
    qa = report.get("qa") or {}
    act = report.get("actions") or {}
    gr = report.get("guardrails") or {}
    lines = [
        "# 评测报告（阶段 5）",
        "",
        f"> 生成时间：{report.get('generated_at')}",
        f"> 命令：`uv run python scripts/run_eval.py`",
        "",
        "## 汇总",
        "",
        f"| 维度 | 结果 | 通过 |",
        f"|------|------|------|",
        f"| QA 引用命中 | {qa.get('citation_hits')}/{qa.get('total')} "
        f"({qa.get('citation_rate')}) | {'✅' if qa.get('pass') else '❌'} |",
        f"| QA 降级 | {qa.get('degraded')}/{qa.get('total')} | — |",
        f"| 行动类型命中 | {act.get('type_hits')}/{act.get('total')} "
        f"({act.get('type_rate')}) | {'✅' if act.get('pass') else '❌' if act else '跳过'} |",
        f"| 行动闸门 | {act.get('gate_hits')}/{act.get('total')} "
        f"({act.get('gate_rate')}) | — |",
        f"| Guardrails | {sum(1 for v in (gr.get('checks') or {}).values() if v)}/"
        f"{len(gr.get('checks') or {})} | {'✅' if gr.get('pass') else '❌'} |",
        f"| **总评** | — | {'✅ PASS' if report.get('pass') else '❌ FAIL'} |",
        "",
        "## QA 明细",
        "",
    ]
    for row in qa.get("rows") or []:
        lines.append(
            f"- {row['id']}: citation={'OK' if row['citation_hit'] else 'MISS'} "
            f"status={row['status']} guard={row.get('guard')}"
        )
    if act:
        lines.extend(["", "## Actions 明细", ""])
        for row in act.get("rows") or []:
            lines.append(
                f"- {row['id']}: type={'OK' if row['type_match'] else 'MISS'} "
                f"gate={'OK' if row['gate_pass'] else 'FAIL'} "
                f"expected={row['expected']} got={row['got']}"
            )
    lines.extend(["", "## Guardrails", ""])
    for k, v in (gr.get("checks") or {}).items():
        lines.append(f"- {k}: {'OK' if v else 'FAIL'}")
    lines.append("")
    return "\n".join(lines)


async def main_async(args: argparse.Namespace) -> int:
    golden = _load_golden()
    qa_items = golden["qa"]
    act_items = golden["actions"]
    if args.limit is not None:
        qa_items = qa_items[: args.limit]
        act_items = act_items[: args.limit]

    _safe_print("=== Phase 5 Eval: QA ===")
    qa_report = await eval_qa(qa_items)

    act_report: dict[str, Any] | None = None
    if not args.skip_actions:
        _safe_print("\n=== Phase 5 Eval: Actions ===")
        act_report = await eval_actions(act_items)

    _safe_print("\n=== Phase 5 Eval: Guardrails ===")
    gr_report = await eval_guardrails()

    overall = bool(qa_report.get("pass") and gr_report.get("pass"))
    if act_report is not None:
        overall = overall and bool(act_report.get("pass"))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "qa": qa_report,
        "actions": act_report or {},
        "guardrails": gr_report,
        "pass": overall,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = REPORT_DIR / f"eval_{stamp}.json"
    latest_json = REPORT_DIR / "latest.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = _render_report(report)
    DOCS_REPORT.write_text(md, encoding="utf-8")
    (REPORT_DIR / "latest.md").write_text(md, encoding="utf-8")

    _safe_print("\n" + md)
    _safe_print(f"\nreport: {DOCS_REPORT}")
    _safe_print(f"json:   {latest_json}")
    _safe_print(f"EVAL_EXIT={'0' if overall else '1'}")
    return 0 if overall else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="黄金集 + Guardrails 评测")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--skip-actions", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
