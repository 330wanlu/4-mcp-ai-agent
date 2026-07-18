"""阶段 6：Chat Console 契约 + 三条主用户故事（经 API）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
CONSOLE = ROOT / "apps" / "chat-console"


@pytest.fixture(scope="module")
def _env_loaded() -> None:
    import os

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    prev_mode = os.environ.get("ORCHESTRATOR_MODE")
    prev_auth = os.environ.get("AUTH_PROVIDER")
    os.environ["ORCHESTRATOR_MODE"] = "local"
    os.environ["AUTH_PROVIDER"] = "dev_header"
    from ka_common.config import get_settings

    get_settings.cache_clear()
    yield
    # 避免污染同进程后续用例（如 phase0 默认 none）
    if prev_mode is None:
        os.environ.pop("ORCHESTRATOR_MODE", None)
    else:
        os.environ["ORCHESTRATOR_MODE"] = prev_mode
    if prev_auth is None:
        os.environ.pop("AUTH_PROVIDER", None)
    else:
        os.environ["AUTH_PROVIDER"] = prev_auth
    get_settings.cache_clear()


@pytest.fixture()
def client(_env_loaded: None) -> TestClient:
    from ka_api.main import create_app

    return TestClient(create_app())


def _headers(user_id: str = "console-tester") -> dict[str, str]:
    return {"X-User-Id": user_id, "X-User-Roles": "employee"}


def test_console_source_has_three_stories() -> None:
    types = (CONSOLE / "src" / "types.ts").read_text(encoding="utf-8")
    app = (CONSOLE / "src" / "App.tsx").read_text(encoding="utf-8")
    api = (CONSOLE / "src" / "api.ts").read_text(encoding="utf-8")

    assert "试用期员工年假怎么算" in types
    assert "差旅制度和报销制度分别管什么" in types
    assert "起草一趟上海出差申请" in types
    assert "引用" in app and "轨迹" in app and "待确认" in app
    assert "/confirm" in api and "/reject" in api and "pending-actions" in api
    assert "X-User-Id" in api


def test_console_package_and_build_artifacts() -> None:
    pkg = json.loads((CONSOLE / "package.json").read_text(encoding="utf-8"))
    assert pkg["name"] == "ka-chat-console"
    assert "dev" in pkg["scripts"] and "build" in pkg["scripts"]
    assert (CONSOLE / "index.html").exists()
    assert (CONSOLE / "vite.config.ts").exists()
    # 构建产物：若已 build 则校验；未 build 时不失败（由 CI/自验证显式 build）
    dist = CONSOLE / "dist" / "index.html"
    if dist.exists():
        html = dist.read_text(encoding="utf-8")
        assert "root" in html


def test_story_qa_via_api(client: TestClient) -> None:
    h = _headers()
    sid = client.post("/chat/sessions", json={"title": "story-qa"}, headers=h).json()[
        "session_id"
    ]
    resp = client.post(
        f"/chat/sessions/{sid}/messages",
        json={"content": "试用期员工年假怎么算？能不能请？", "top_k": 5},
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["answer"]
    assert body["citations"], "问答应带回引用"
    agents = {s.get("agent") for s in body.get("agent_trace") or []}
    assert "router" in agents and "researcher" in agents and "analyst" in agents
    assert body.get("status") in ("completed", "degraded")


def test_story_compare_via_api(client: TestClient) -> None:
    h = _headers("console-compare")
    sid = client.post("/chat/sessions", json={"title": "story-compare"}, headers=h).json()[
        "session_id"
    ]
    resp = client.post(
        f"/chat/sessions/{sid}/messages",
        json={
            "content": "差旅制度和报销制度分别管什么？出差请客户吃饭记哪个科目？",
            "top_k": 5,
        },
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["answer"]
    assert body["citations"]
    agents = [s.get("agent") for s in body.get("agent_trace") or []]
    assert "researcher" in agents and "analyst" in agents


def test_story_action_confirm_gate_via_api(client: TestClient) -> None:
    from ka_business_mcp.service import count_tickets

    h = _headers("console-action")
    sid = client.post("/chat/sessions", json={"title": "story-action"}, headers=h).json()[
        "session_id"
    ]
    resp = client.post(
        f"/chat/sessions/{sid}/messages",
        json={
            "content": "按差旅政策起草一趟上海出差申请，并创建待办提醒我提交审批。",
            "top_k": 5,
        },
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("status") == "awaiting_confirmation"
    assert body.get("pending_action"), "应返回待确认行动"
    assert count_tickets(session_id=sid) == 0

    pending = client.get(f"/chat/sessions/{sid}/pending-actions", headers=h).json()
    assert pending.get("pending_actions")

    confirmed = client.post(f"/chat/sessions/{sid}/confirm", headers=h)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json().get("ok") is True
    assert count_tickets(session_id=sid) >= 1

    agents = {s.get("agent") for s in body.get("agent_trace") or []}
    assert "executor" in agents or "critic_guard" in agents
