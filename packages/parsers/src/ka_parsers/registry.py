"""解析器注册表；PDF/DOCX 可在此挂载。"""

from __future__ import annotations

from pathlib import Path

from ka_parsers.base import DocumentParser
from ka_parsers.markdown import MarkdownParser
from ka_parsers.text import TextParser

_REGISTRY: dict[str, DocumentParser] = {
    "markdown": MarkdownParser(),
    "text": TextParser(),
}


def list_parsers() -> list[str]:
    return sorted(_REGISTRY.keys())


def get_parser(name: str) -> DocumentParser:
    if name not in _REGISTRY:
        raise KeyError(f"未知解析器: {name}；可用: {list_parsers()}")
    return _REGISTRY[name]


def resolve_parser(path: Path) -> DocumentParser:
    for parser in _REGISTRY.values():
        if parser.can_parse(path):
            return parser
    raise ValueError(f"无可用解析器: {path}（阶段 0/1 仅支持 md/txt）")
