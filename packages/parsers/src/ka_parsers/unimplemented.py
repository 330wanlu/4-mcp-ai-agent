"""PDF/DOCX 占位：阶段 1 未实现，仅保留扩展点。"""

from __future__ import annotations

from pathlib import Path

from ka_parsers.base import DocumentParser, ParsedDocument


class PdfParser(DocumentParser):
    name = "pdf"
    suffixes = (".pdf",)

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() in self.suffixes

    def parse(self, path: Path) -> ParsedDocument:
        raise NotImplementedError("PDF 解析延后；请使用 Markdown/纯文本语料")


class DocxParser(DocumentParser):
    name = "docx"
    suffixes = (".docx",)

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() in self.suffixes

    def parse(self, path: Path) -> ParsedDocument:
        raise NotImplementedError("DOCX 解析延后；请使用 Markdown/纯文本语料")
