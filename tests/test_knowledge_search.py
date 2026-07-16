"""阶段 1：知识入库与检索测试。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def _env_loaded() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")


def test_tables_exist(_env_loaded: None) -> None:
    from ka_common.db.session import get_engine

    engine = get_engine()
    with engine.connect() as conn:
        for table in ("documents", "chunks", "audit_logs", "tickets", "users"):
            exists = conn.execute(
                text("SELECT to_regclass(:name)"), {"name": f"public.{table}"}
            ).scalar()
            assert exists == table, f"缺少表 {table}"


def test_ingested_documents_at_least_five(_env_loaded: None) -> None:
    from ka_common.db import Document
    from ka_common.db.session import session_scope

    with session_scope() as session:
        count = session.scalar(select(func.count()).select_from(Document)) or 0
    assert count >= 5, f"入库文档不足 5 篇，当前 {count}；请先 ingest_docs.py"


def test_chunks_have_embeddings(_env_loaded: None) -> None:
    from ka_common.db import Chunk
    from ka_common.db.session import session_scope

    with session_scope() as session:
        total = session.scalar(select(func.count()).select_from(Chunk)) or 0
        with_emb = session.scalar(
            select(func.count()).select_from(Chunk).where(Chunk.embedding.is_not(None))
        ) or 0
    assert total > 0
    assert with_emb == total


def test_hybrid_search_returns_required_fields(_env_loaded: None) -> None:
    from ka_knowledge_mcp.service import hybrid_search

    hits = asyncio.run(hybrid_search("差旅报销", top_k=3))
    assert hits, "检索应有结果"
    for h in hits:
        assert "doc_id" in h and h["doc_id"]
        assert "title" in h and h["title"]
        assert "section" in h
        assert "score" in h and isinstance(h["score"], float)


def test_list_sources_and_get_section(_env_loaded: None) -> None:
    from ka_knowledge_mcp.service import get_document_section, list_sources

    sources = list_sources()
    assert len(sources) >= 5
    doc_id = sources[0]["doc_id"]
    section = get_document_section(doc_id)
    assert section["found"] is True
    assert section["content"]


def test_knowledge_http_tools_shape(_env_loaded: None) -> None:
    from fastapi.testclient import TestClient

    from ka_knowledge_mcp.server import create_app

    client = TestClient(create_app())
    assert client.get("/health").json()["status"] == "ok"
    tools = client.get("/tools").json()["tools"]
    assert set(tools) >= {"hybrid_search", "get_document_section", "list_sources"}
    listed = client.get("/tools/list_sources").json()
    assert listed["count"] >= 5
