"""纯文本解析器。"""

from __future__ import annotations

from pathlib import Path

from ka_parsers.base import DocumentParser, ParsedDocument, ParsedSection


class TextParser(DocumentParser):
    name = "text"
    suffixes = (".txt",)

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() in self.suffixes

    def parse(self, path: Path) -> ParsedDocument:
        text = path.read_text(encoding="utf-8")
        return ParsedDocument(
            path=str(path),
            title=path.stem,
            sections=[ParsedSection(title=path.stem, content=text.strip(), level=1)],
            raw_text=text,
        )
