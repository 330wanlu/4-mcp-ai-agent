#!/usr/bin/env python3
"""将 data/corpus 下 Markdown/Text 入库到 Postgres + PGVector。

用法:
  uv run python scripts/ingest_docs.py
  uv run python scripts/ingest_docs.py --corpus data/corpus --force
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from ka_common.db import Chunk, Document, ensure_vector_extension, session_scope  # noqa: E402
from ka_common.db.session import get_engine  # noqa: E402
from ka_llm import VolcengineDoubaoProvider  # noqa: E402
from ka_parsers import chunk_parsed_document, resolve_parser  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402


def _domain_from_path(path: Path, corpus_root: Path) -> str:
    try:
        rel = path.relative_to(corpus_root)
        return rel.parts[0] if len(rel.parts) > 1 else "general"
    except ValueError:
        return "general"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _iter_corpus_files(corpus_root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("**/*.md", "**/*.markdown", "**/*.txt"):
        files.extend(corpus_root.glob(pattern))
    return sorted({p.resolve() for p in files if p.is_file()})


async def ingest(corpus_root: Path, *, force: bool = False) -> dict[str, int]:
    ensure_vector_extension()
    # 触发 metadata 绑定
    get_engine()

    files = _iter_corpus_files(corpus_root)
    if not files:
        raise SystemExit(f"语料目录为空: {corpus_root}")

    provider = VolcengineDoubaoProvider()
    stats = {"files": 0, "skipped": 0, "chunks": 0, "embedded": 0}

    for path in files:
        parser = resolve_parser(path)
        parsed = parser.parse(path)
        text = parsed.raw_text or ""
        digest = _content_hash(text)
        rel_path = str(path.relative_to(ROOT)).replace("\\", "/")
        domain = _domain_from_path(path, corpus_root)

        with session_scope() as session:
            existing = session.scalar(
                select(Document).where(Document.source_path == rel_path)
            )
            if existing and existing.content_hash == digest and not force:
                print(f"[skip] 未变更: {rel_path}")
                stats["skipped"] += 1
                continue

            chunks = chunk_parsed_document(parsed)
            if not chunks:
                print(f"[warn] 无切片: {rel_path}")
                stats["skipped"] += 1
                continue

            print(f"[ingest] {rel_path} -> {len(chunks)} chunks ...")
            embeddings = await provider.embed([c.content for c in chunks])
            stats["embedded"] += len(embeddings)

            if existing:
                session.execute(delete(Chunk).where(Chunk.document_id == existing.id))
                existing.title = parsed.title
                existing.domain = domain
                existing.content_hash = digest
                existing.raw_text = text
                existing.meta = {"filename": path.name}
                doc = existing
            else:
                doc = Document(
                    title=parsed.title,
                    source_path=rel_path,
                    domain=domain,
                    content_hash=digest,
                    raw_text=text,
                    meta={"filename": path.name},
                )
                session.add(doc)
                session.flush()

            for ch, vec in zip(chunks, embeddings, strict=True):
                session.add(
                    Chunk(
                        document_id=doc.id,
                        chunk_index=ch.chunk_index,
                        section=ch.section,
                        content=ch.content,
                        token_estimate=max(1, len(ch.content) // 2),
                        embedding=vec,
                        meta={"filename": path.name},
                    )
                )
            stats["files"] += 1
            stats["chunks"] += len(chunks)
            print(f"[ok] {path.name}: {len(chunks)} chunks")

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest corpus into PGVector")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=ROOT / "data" / "corpus",
        help="语料根目录",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="即使 content_hash 未变也重新嵌入入库",
    )
    args = parser.parse_args()
    corpus = args.corpus if args.corpus.is_absolute() else ROOT / args.corpus
    stats = asyncio.run(ingest(corpus, force=args.force))
    print(
        f"完成: files={stats['files']} skipped={stats['skipped']} "
        f"chunks={stats['chunks']} embedded={stats['embedded']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
