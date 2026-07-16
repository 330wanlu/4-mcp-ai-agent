"""DocumentParser 协议；PDF/DOCX 后续再实现。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedSection:
    title: str
    content: str
    level: int = 1


@dataclass
class ParsedDocument:
    path: str
    title: str
    sections: list[ParsedSection] = field(default_factory=list)
    raw_text: str = ""


class DocumentParser(ABC):
    """可插拔文档解析器。MVP 仅 Markdown / Text。"""

    name: str
    suffixes: tuple[str, ...]

    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, path: Path) -> ParsedDocument:
        raise NotImplementedError
