"""RTF parser adapter using striprtf."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from adx.models.document import FileType
from adx.parsers.base import (
    ParserAdapter,
    ParserCapabilities,
    ParserResult,
    ParserWarning,
)

logger = logging.getLogger(__name__)


class RTFAdapter(ParserAdapter):
    """Parser adapter for RTF files using striprtf."""

    def name(self) -> str:
        return "striprtf"

    def version(self) -> str:
        try:
            import striprtf

            return getattr(striprtf, "__version__", "unknown")
        except ImportError:
            return "not installed"

    def capabilities(self) -> ParserCapabilities:
        return ParserCapabilities(
            supported_types=[FileType.RTF],
            extracts_text=True,
            extracts_tables=False,
            extracts_layout=False,
            extracts_formulas=False,
            extracts_images=False,
            supports_ocr=False,
        )

    def parse(self, file_path: Path, file_type: FileType) -> ParserResult:
        result = ParserResult(
            parser_name=self.name(),
            parser_version=self.version(),
            file_type=file_type,
        )

        try:
            from striprtf.striprtf import rtf_to_text
        except ImportError:
            result.errors.append("striprtf is not installed. Run: pip install striprtf")
            return result

        # Read the raw RTF content
        try:
            raw = file_path.read_bytes()
        except Exception as e:
            result.errors.append(f"Failed to read RTF file: {e}")
            return result

        # Decode with fallback
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("latin-1")
            except Exception as e:
                result.errors.append(f"Failed to decode RTF: {e}")
                return result

        # Strip RTF formatting
        try:
            plain = rtf_to_text(text)
        except Exception as e:
            result.errors.append(f"Failed to parse RTF content: {e}")
            return result

        # Split into paragraphs
        paragraphs = [line.strip() for line in plain.split("\n") if line.strip()]

        if not paragraphs:
            result.warnings.append(
                ParserWarning(code="EMPTY_DOCUMENT", message="RTF contains no text.")
            )
            result.page_count = 1
            result.pages.append({
                "page_number": 1,
                "width": 612,
                "height": 792,
                "text_blocks": [],
                "tables": [],
            })
            return result

        text_blocks: list[dict[str, Any]] = []
        for idx, para in enumerate(paragraphs):
            text_blocks.append({
                "text": para,
                "block_type": "paragraph",
                "heading_level": 0,
                "page_number": 1,
                "bbox": None,
                "font_size": 12.0,
                "confidence": 0.8,  # Lower confidence since formatting is stripped
                "block_index": idx,
            })

        page_data: dict[str, Any] = {
            "page_number": 1,
            "width": 612,
            "height": 792,
            "text_blocks": text_blocks,
            "tables": [],
        }

        result.pages.append(page_data)
        result.text_blocks.extend(text_blocks)
        result.page_count = 1
        result.metadata = {
            "paragraph_count": len(paragraphs),
            "char_count": sum(len(p) for p in paragraphs),
        }

        return result
