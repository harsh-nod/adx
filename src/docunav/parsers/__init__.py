"""Parser adapter layer. Wraps external parsing engines behind a unified interface."""

from docunav.parsers.base import ParserAdapter, ParserCapabilities, ParserResult
from docunav.parsers.registry import ParserRegistry

__all__ = ["ParserAdapter", "ParserCapabilities", "ParserResult", "ParserRegistry"]
