"""文档切片：按章节，过长再按字符窗口切分。"""

from __future__ import annotations

from dataclasses import dataclass

from ka_parsers.base import ParsedDocument


@dataclass
class TextChunk:
    section: str
    content: str
    chunk_index: int


def chunk_parsed_document(
    doc: ParsedDocument,
    *,
    max_chars: int = 800,
    overlap: int = 100,
) -> list[TextChunk]:
    """将 ParsedDocument 转为入库切片。"""
    raw_pieces: list[tuple[str, str]] = []
    if doc.sections:
        for sec in doc.sections:
            title = sec.title or doc.title
            body = (sec.content or "").strip()
            if not body:
                continue
            raw_pieces.append((title, body))
    else:
        text = (doc.raw_text or "").strip()
        if text:
            raw_pieces.append((doc.title, text))

    out: list[TextChunk] = []
    idx = 0
    for section, body in raw_pieces:
        if len(body) <= max_chars:
            out.append(TextChunk(section=section, content=body, chunk_index=idx))
            idx += 1
            continue
        start = 0
        while start < len(body):
            end = min(len(body), start + max_chars)
            piece = body[start:end].strip()
            if piece:
                out.append(TextChunk(section=section, content=piece, chunk_index=idx))
                idx += 1
            if end >= len(body):
                break
            start = max(0, end - overlap)
    return out
