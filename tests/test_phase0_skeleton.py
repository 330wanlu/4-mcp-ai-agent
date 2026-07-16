# 阶段 0 冒烟：骨架、语料、黄金集、扩展点可导入

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_corpus_has_at_least_five_markdown_files() -> None:
    corpus = ROOT / "data" / "corpus"
    files = list(corpus.rglob("*.md"))
    assert len(files) >= 5, f"语料 md 数量不足: {len(files)}"


def test_golden_set_counts() -> None:
    data = json.loads((ROOT / "data" / "golden_set" / "golden_set.json").read_text(encoding="utf-8"))
    assert len(data["qa"]) == 10
    assert len(data["actions"]) == 5
    for item in data["qa"]:
        assert item["source_docs"], item["id"]
        assert item["question"]
    for item in data["actions"]:
        assert item["source_docs"], item["id"]
        assert item["task"]


def test_golden_source_docs_exist() -> None:
    data = json.loads((ROOT / "data" / "golden_set" / "golden_set.json").read_text(encoding="utf-8"))
    corpus_names = {p.name for p in (ROOT / "data" / "corpus").rglob("*.md")}
    missing: list[str] = []
    for group in ("qa", "actions"):
        for item in data[group]:
            for name in item["source_docs"]:
                if name not in corpus_names:
                    missing.append(f"{item['id']}:{name}")
    assert not missing, f"黄金集引用了不存在的语料: {missing}"


def test_extension_points_importable() -> None:
    from ka_auth import NoAuthProvider, get_auth_provider
    from ka_llm import VolcengineDoubaoProvider
    from ka_parsers import MarkdownParser, list_parsers
    from ka_orchestrator.graph import AGENT_GRAPH_SUMMARY

    assert "markdown" in list_parsers()
    doc = MarkdownParser().parse(next((ROOT / "data" / "corpus").rglob("*.md")))
    assert doc.sections
    assert get_auth_provider().name == "none"
    assert NoAuthProvider().name == "none"
    assert VolcengineDoubaoProvider().settings.llm_model
    assert "router" in AGENT_GRAPH_SUMMARY["nodes"]


def test_api_health_and_me() -> None:
    from fastapi.testclient import TestClient

    from ka_api.main import create_app

    client = TestClient(create_app())
    assert client.get("/health").json()["status"] == "ok"
    me = client.get("/me").json()
    assert me["user_id"] == "local-dev"
