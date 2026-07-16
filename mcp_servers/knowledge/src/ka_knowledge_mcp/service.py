"""Knowledge 检索服务：hybrid_search / get_document_section / list_sources。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from ka_common.db.models import Chunk, Document
from ka_common.db.session import session_scope
from ka_llm import VolcengineDoubaoProvider


@dataclass
class SearchHit:
    doc_id: str
    title: str
    section: str | None
    score: float
    snippet: str
    source_path: str
    filename: str | None = None


def _snippet(content: str, limit: int = 240) -> str:
    content = " ".join(content.split())
    return content if len(content) <= limit else content[: limit - 1] + "…"


def list_sources(session: Session | None = None) -> list[dict[str, Any]]:
    def _run(s: Session) -> list[dict[str, Any]]:
        rows = s.scalars(select(Document).order_by(Document.domain, Document.title)).all()
        return [
            {
                "doc_id": d.id,
                "title": d.title,
                "domain": d.domain,
                "source_path": d.source_path,
                "filename": (d.meta or {}).get("filename"),
            }
            for d in rows
        ]

    if session is not None:
        return _run(session)
    with session_scope() as s:
        return _run(s)


def get_document_section(
    doc_id: str,
    section: str | None = None,
    *,
    session: Session | None = None,
) -> dict[str, Any]:
    def _run(s: Session) -> dict[str, Any]:
        doc = s.get(Document, doc_id)
        if doc is None:
            return {"found": False, "doc_id": doc_id, "error": "document not found"}

        stmt: Select[tuple[Chunk]] = (
            select(Chunk)
            .where(Chunk.document_id == doc_id)
            .order_by(Chunk.chunk_index)
        )
        if section:
            stmt = stmt.where(Chunk.section.ilike(f"%{section}%"))

        chunks = s.scalars(stmt).all()
        if not chunks:
            return {
                "found": False,
                "doc_id": doc_id,
                "title": doc.title,
                "section": section,
                "error": "section not found",
            }

        return {
            "found": True,
            "doc_id": doc.id,
            "title": doc.title,
            "source_path": doc.source_path,
            "section": section or chunks[0].section,
            "content": "\n\n".join(c.content for c in chunks),
            "chunk_count": len(chunks),
        }

    if session is not None:
        return _run(session)
    with session_scope() as s:
        return _run(s)


async def hybrid_search(
    query: str,
    *,
    top_k: int = 5,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
    session: Session | None = None,
    provider: VolcengineDoubaoProvider | None = None,
) -> list[dict[str, Any]]:
    """向量相似度 + 关键词命中的混合检索。"""
    provider = provider or VolcengineDoubaoProvider()
    query = (query or "").strip()
    if not query:
        return []

    vectors = await provider.embed([query])
    qvec = vectors[0]

    def _run(s: Session) -> list[SearchHit]:
        # cosine distance: smaller is better -> score = 1 / (1 + distance)
        distance = Chunk.embedding.cosine_distance(qvec)
        vec_stmt = (
            select(
                Chunk,
                Document,
                distance.label("distance"),
            )
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.embedding.is_not(None))
            .order_by(distance)
            .limit(max(top_k * 4, 20))
        )
        vec_rows = s.execute(vec_stmt).all()

        tokens = [t for t in query.replace("，", " ").replace("。", " ").split() if t]
        kw_map: dict[str, float] = {}
        if tokens:
            like_clauses = [Chunk.content.ilike(f"%{t}%") for t in tokens]
            # also match section / title
            like_clauses.extend(Document.title.ilike(f"%{t}%") for t in tokens)
            kw_stmt = (
                select(Chunk.id, Chunk.content, Document.title)
                .join(Document, Document.id == Chunk.document_id)
                .where(or_(*like_clauses))
            )
            for cid, content, title in s.execute(kw_stmt).all():
                hit = sum(1 for t in tokens if t.lower() in (content or "").lower())
                hit += sum(1 for t in tokens if t.lower() in (title or "").lower())
                kw_map[str(cid)] = hit / max(len(tokens), 1)

        merged: dict[str, SearchHit] = {}
        for chunk, doc, dist in vec_rows:
            vec_score = 1.0 / (1.0 + float(dist))
            kw_score = kw_map.get(str(chunk.id), 0.0)
            score = vector_weight * vec_score + keyword_weight * kw_score
            merged[str(chunk.id)] = SearchHit(
                doc_id=str(doc.id),
                title=doc.title,
                section=chunk.section,
                score=round(score, 6),
                snippet=_snippet(chunk.content),
                source_path=doc.source_path,
                filename=(doc.meta or {}).get("filename")
                or (chunk.meta or {}).get("filename"),
            )

        # include pure keyword hits not in vector top
        if kw_map:
            missing_ids = [cid for cid in kw_map if cid not in merged]
            if missing_ids:
                rows = s.execute(
                    select(Chunk, Document)
                    .join(Document, Document.id == Chunk.document_id)
                    .where(Chunk.id.in_(missing_ids))
                ).all()
                for chunk, doc in rows:
                    score = keyword_weight * kw_map[str(chunk.id)]
                    merged[str(chunk.id)] = SearchHit(
                        doc_id=str(doc.id),
                        title=doc.title,
                        section=chunk.section,
                        score=round(score, 6),
                        snippet=_snippet(chunk.content),
                        source_path=doc.source_path,
                        filename=(doc.meta or {}).get("filename"),
                    )

        hits = sorted(merged.values(), key=lambda h: h.score, reverse=True)[:top_k]
        return hits

    if session is not None:
        hits = _run(session)
    else:
        with session_scope() as s:
            hits = _run(s)
    return [asdict(h) for h in hits]


TOOLS = ("hybrid_search", "get_document_section", "list_sources")
