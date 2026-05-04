"""Parser adapter layer. Wraps external parsing engines behind a unified interface."""

from adx.parsers.base import ParserAdapter, ParserCapabilities, ParserResult
from adx.parsers.docx_adapter import DocxAdapter
from adx.parsers.registry import ParserRegistry
from adx.parsers.rtf_adapter import RTFAdapter

__all__ = [
    "ParserAdapter",
    "ParserCapabilities",
    "ParserResult",
    "ParserRegistry",
    "DocxAdapter",
    "RTFAdapter",
]
