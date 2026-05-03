"""Base parser adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docunav.models.document import FileType


@dataclass
class ParserCapabilities:
    supported_types: list[FileType]
    extracts_text: bool = True
    extracts_tables: bool = False
    extracts_layout: bool = False
    extracts_formulas: bool = False
    extracts_images: bool = False
    supports_ocr: bool = False


@dataclass
class ParserWarning:
    code: str
    message: str
    page: int | None = None
    sheet: str | None = None


@dataclass
class ParserResult:
    """Normalized output from any parser adapter."""

    parser_name: str
    parser_version: str
    file_type: FileType
    raw_output: Any = None

    # PDF-oriented outputs
    pages: list[dict[str, Any]] = field(default_factory=list)
    text_blocks: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    figures: list[dict[str, Any]] = field(default_factory=list)

    # Spreadsheet-oriented outputs
    sheets: list[dict[str, Any]] = field(default_factory=list)
    cells: list[dict[str, Any]] = field(default_factory=list)
    formulas: list[dict[str, Any]] = field(default_factory=list)
    named_ranges: dict[str, str] = field(default_factory=dict)
    external_links: list[str] = field(default_factory=list)

    # Metadata
    page_count: int = 0
    sheet_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[ParserWarning] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class ParserAdapter(ABC):
    """Base class for all parser adapters."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    def capabilities(self) -> ParserCapabilities: ...

    def supports(self, file_type: FileType) -> bool:
        return file_type in self.capabilities().supported_types

    @abstractmethod
    def parse(self, file_path: Path, file_type: FileType) -> ParserResult: ...
