# 评测报告（阶段 5）

> 生成时间：2026-07-18T08:19:43.549707+00:00
> 命令：`uv run python scripts/run_eval.py`

## 汇总

| 维度 | 结果 | 通过 |
|------|------|------|
| QA 引用命中 | 10/10 (1.0) | ✅ |
| QA 降级 | 0/10 | — |
| 行动类型命中 | 5/5 (1.0) | ✅ |
| 行动闸门 | 5/5 (1.0) | — |
| Guardrails | 4/4 | ✅ |
| **总评** | — | ✅ PASS |

## QA 明细

- QA-01: citation=OK status=completed guard=pass
- QA-02: citation=OK status=completed guard=pass
- QA-03: citation=OK status=completed guard=pass
- QA-04: citation=OK status=completed guard=pass
- QA-05: citation=OK status=completed guard=pass
- QA-06: citation=OK status=completed guard=pass
- QA-07: citation=OK status=completed guard=pass
- QA-08: citation=OK status=completed guard=pass
- QA-09: citation=OK status=completed guard=pass
- QA-10: citation=OK status=completed guard=pass

## Actions 明细

- ACT-01: type=OK gate=OK expected=create_travel_draft_and_todo got=create_travel_draft_and_todo
- ACT-02: type=OK gate=OK expected=create_leave_draft_and_todo got=create_leave_draft_and_todo
- ACT-03: type=OK gate=OK expected=create_ticket got=create_ticket
- ACT-04: type=OK gate=OK expected=create_document_draft_and_todo got=create_document_draft_and_todo
- ACT-05: type=OK gate=OK expected=refuse_or_require_travel_order got=refuse_or_require_travel_order

## Guardrails

- answer_guard_no_citation: OK
- action_guard_block: OK
- memory_upsert_get: OK
- pipeline_out_of_domain_degrade: OK
