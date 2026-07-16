"""文档解析扩展点。"""

from ka_parsers.base import DocumentParser, ParsedDocument, ParsedSection
from ka_parsers.markdown import MarkdownParser
from ka_parsers.registry import get_parser, list_parsers
from ka_parsers.text import TextParser

__all__ = [
    "DocumentParser",
    "ParsedDocument",
    "ParsedSection",
    "MarkdownParser",
    "TextParser",
    "get_parser",
    "list_parsers",
]
