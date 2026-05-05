"""Parser registry — selects the right adapter for each file type."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from adx.models.document import FileType
from adx.parsers.base import ParserAdapter, ParserResult
from adx.parsers.csv_adapter import CSVAdapter
from adx.parsers.docx_adapter import DocxAdapter
from adx.parsers.excel_adapter import OpenpyxlAdapter
from adx.parsers.pdf_adapter import PyMuPDFAdapter
from adx.parsers.pptx_adapter import PptxAdapter
from adx.parsers.rtf_adapter import RTFAdapter
from adx.parsers.xls_adapter import XlrdAdapter

logger = logging.getLogger(__name__)

# Maximum file size: 500 MB
MAX_FILE_SIZE: int = 500 * 1024 * 1024

# Map MIME types to FileTypes for cross-validation
MIME_TO_FILE_TYPE: dict[str, FileType] = {
    "application/pdf": FileType.PDF,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.XLSX,
    "application/vnd.ms-excel": FileType.XLS,
    "text/csv": FileType.CSV,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileType.DOCX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": FileType.PPTX,
    "application/rtf": FileType.RTF,
    "text/rtf": FileType.RTF,
    "text/plain": FileType.TEXT,
    "image/png": FileType.IMAGE,
    "image/jpeg": FileType.IMAGE,
    "image/tiff": FileType.IMAGE,
}

EXTENSION_MAP: dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".xlsx": FileType.XLSX,
    ".xls": FileType.XLS,
    ".csv": FileType.CSV,
    ".docx": FileType.DOCX,
    ".pptx": FileType.PPTX,
    ".rtf": FileType.RTF,
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
            DocxAdapter(),
            PptxAdapter(),
            RTFAdapter(),
            XlrdAdapter(),
        ]

    def register(self, adapter: ParserAdapter) -> None:
        self._adapters.insert(0, adapter)

    def detect_file_type(self, file_path: Path) -> FileType:
        # Check file size
        try:
            size = file_path.stat().st_size
        except OSError:
            size = 0
        if size > MAX_FILE_SIZE:
            raise ValueError(
                f"File too large ({size / (1024 * 1024):.1f} MB). "
                f"Maximum allowed size is {MAX_FILE_SIZE / (1024 * 1024):.0f} MB."
            )

        ext = file_path.suffix.lower()
        file_type = EXTENSION_MAP.get(ext, FileType.UNKNOWN)

        # Cross-check with MIME sniffing
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and mime_type in MIME_TO_FILE_TYPE:
            mime_file_type = MIME_TO_FILE_TYPE[mime_type]
            if file_type != FileType.UNKNOWN and mime_file_type != file_type:
                logger.warning(
                    "MIME type %s suggests %s but extension suggests %s for %s; "
                    "using extension-based type",
                    mime_type,
                    mime_file_type.value,
                    file_type.value,
                    file_path.name,
                )

        return file_type

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
