"""文档解析扩展点。"""

from ka_parsers.base import DocumentParser, ParsedDocument, ParsedSection
from ka_parsers.chunking import TextChunk, chunk_parsed_document
from ka_parsers.markdown import MarkdownParser
from ka_parsers.registry import get_parser, list_parsers, resolve_parser
from ka_parsers.text import TextParser
from ka_parsers.unimplemented import DocxParser, PdfParser

__all__ = [
    "DocumentParser",
    "ParsedDocument",
    "ParsedSection",
    "MarkdownParser",
    "TextParser",
    "PdfParser",
    "DocxParser",
    "TextChunk",
    "chunk_parsed_document",
    "get_parser",
    "list_parsers",
    "resolve_parser",
]
