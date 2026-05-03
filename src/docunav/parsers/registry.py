"""Parser registry — selects the right adapter for each file type."""

from __future__ import annotations

import logging
from pathlib import Path

from docunav.models.document import FileType
from docunav.parsers.base import ParserAdapter, ParserResult
from docunav.parsers.csv_adapter import CSVAdapter
from docunav.parsers.excel_adapter import OpenpyxlAdapter
from docunav.parsers.pdf_adapter import PyMuPDFAdapter

logger = logging.getLogger(__name__)

EXTENSION_MAP: dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".xlsx": FileType.XLSX,
    ".xls": FileType.XLS,
    ".csv": FileType.CSV,
    ".docx": FileType.DOCX,
    ".txt": FileType.TEXT,
    ".png": FileType.IMAGE,
    ".jpg": FileType.IMAGE,
    ".jpeg": FileType.IMAGE,
    ".tiff": FileType.IMAGE,
    ".tif": FileType.IMAGE,
}


class ParserRegistry:
    """Registry of parser adapters with automatic selection and fallback."""

    def __init__(self) -> None:
        self._adapters: list[ParserAdapter] = [
            PyMuPDFAdapter(),
            OpenpyxlAdapter(),
            CSVAdapter(),
        ]

    def register(self, adapter: ParserAdapter) -> None:
        self._adapters.insert(0, adapter)

    def detect_file_type(self, file_path: Path) -> FileType:
        ext = file_path.suffix.lower()
        return EXTENSION_MAP.get(ext, FileType.UNKNOWN)

    def get_adapter(self, file_type: FileType) -> ParserAdapter | None:
        for adapter in self._adapters:
            if adapter.supports(file_type):
                return adapter
        return None

    def parse(self, file_path: Path, file_type: FileType | None = None) -> ParserResult:
        if file_type is None:
            file_type = self.detect_file_type(file_path)

        adapter = self.get_adapter(file_type)
        if adapter is None:
            return ParserResult(
                parser_name="none",
                parser_version="0",
                file_type=file_type,
                errors=[f"No parser available for file type: {file_type.value}"],
            )

        logger.info("Parsing %s with %s", file_path.name, adapter.name())
        return adapter.parse(file_path, file_type)
