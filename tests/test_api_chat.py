"""阶段 3：FastAPI Chat / 审计 / Debug 测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def _env_loaded() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    # pytest 默认走 local，避免依赖已启动的 :8001
    import os

    os.environ["ORCHESTRATOR_MODE"] = "local"
    from ka_common.config import get_settings

    get_settings.cache_clear()


@pytest.fixture()
def client(_env_loaded: None) -> TestClient:
    from ka_api.main import create_app

    return TestClient(create_app())


def test_health_and_me(client: TestClient) -> None:
    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["phase"] == "6"
    me = client.get("/me").json()
    assert me["user_id"] == "local-dev"


def test_auth_extension_dev_header(monkeypatch: pytest.MonkeyPatch, _env_loaded: None) -> None:
    monkeypatch.setenv("AUTH_PROVIDER", "dev_header")
    from ka_common.config import get_settings

    get_settings.cache_clear()
    from ka_api.main import create_app

    c = TestClient(create_app())
    me = c.get("/me", headers={"X-User-Id": "alice"}).json()
    assert me["user_id"] == "alice"
    # 恢复
    monkeypatch.setenv("AUTH_PROVIDER", "none")
    get_settings.cache_clear()


def test_chat_flow_create_ask_get(client: TestClient) -> None:
    created = client.post("/chat/sessions", json={"title": "试用期年假"}).json()
    session_id = created["session_id"]
    assert created["status"] == "created"
    assert session_id

    posted = client.post(
        f"/chat/sessions/{session_id}/messages",
        json={"content": "试用期员工年假怎么算？能不能请？", "top_k": 5},
    )
    assert posted.status_code == 200, posted.text
    body = posted.json()
    assert body["session_id"] == session_id
    assert body["answer"]
    assert body["citations"], "应带回引用"
    assert body["agent_trace"]
    agents = [s["agent"] for s in body["agent_trace"]]
    for required in ("memory", "router", "researcher", "analyst", "critic_guard"):
        assert required in agents, f"缺少 agent: {required}, got={agents}"

    detail = client.get(f"/chat/sessions/{session_id}").json()
    assert detail["found"] is True
    assert detail["answer"]
    assert detail["citations"]
    assert detail["agent_trace"]
    assert detail["status"] in ("completed", "degraded")

    debug = client.get(f"/debug/sessions/{session_id}").json()
    assert debug["found"] is True
    assert debug["state"]["session_id"] == session_id
    assert "agent_trace" in debug["state"]

    audit = client.get("/audit/events", params={"session_id": session_id, "limit": 20}).json()
    assert audit["count"] >= 1
    types = {e["event_type"] for e in audit["events"]}
    assert "qa_complete" in types


def test_session_not_found(client: TestClient) -> None:
    resp = client.get("/chat/sessions/does-not-exist")
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert err["code"] == "SESSION_NOT_FOUND"

    resp2 = client.post(
        "/chat/sessions/does-not-exist/messages",
        json={"content": "hello"},
    )
    assert resp2.status_code == 404


def test_openapi_docs_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/chat/sessions" in paths
    assert "/chat/sessions/{session_id}/messages" in paths
    assert "/audit/events" in paths
    assert "/debug/sessions/{session_id}" in paths
    assert "/chat/sessions/{session_id}/pending-actions" in paths
    assert "/chat/sessions/{session_id}/confirm" in paths
    assert "/chat/sessions/{session_id}/reject" in paths
