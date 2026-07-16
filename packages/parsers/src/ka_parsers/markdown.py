"""Markdown 解析器：按 ATx 标题粗分章节。"""

from __future__ import annotations

import re
from pathlib import Path

from ka_parsers.base import DocumentParser, ParsedDocument, ParsedSection

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


class MarkdownParser(DocumentParser):
    name = "markdown"
    suffixes = (".md", ".markdown")

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() in self.suffixes

    def parse(self, path: Path) -> ParsedDocument:
        text = path.read_text(encoding="utf-8")
        title = path.stem
        sections: list[ParsedSection] = []

        matches = list(_HEADING.finditer(text))
        if not matches:
            sections.append(ParsedSection(title=title, content=text.strip(), level=1))
        else:
            first = matches[0]
            if first.group(2).strip():
                title = first.group(2).strip()
            for i, m in enumerate(matches):
                start = m.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                body = text[start:end].strip()
                sections.append(
                    ParsedSection(
                        title=m.group(2).strip(),
                        content=body,
                        level=len(m.group(1)),
                    )
                )

        return ParsedDocument(
            path=str(path),
            title=title,
            sections=sections,
            raw_text=text,
        )
