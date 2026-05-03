"""PDF parser adapter using PyMuPDF (fitz)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from docunav.models.document import FileType
from docunav.parsers.base import (
    ParserAdapter,
    ParserCapabilities,
    ParserResult,
    ParserWarning,
)

logger = logging.getLogger(__name__)


class PyMuPDFAdapter(ParserAdapter):
    """Wraps PyMuPDF for PDF text, layout, and table extraction."""

    def name(self) -> str:
        return "pymupdf"

    def version(self) -> str:
        try:
            import fitz
            return fitz.VersionBind
        except Exception:
            return "unknown"

    def capabilities(self) -> ParserCapabilities:
        return ParserCapabilities(
            supported_types=[FileType.PDF],
            extracts_text=True,
            extracts_tables=True,
            extracts_layout=True,
            extracts_formulas=False,
            extracts_images=True,
            supports_ocr=False,
        )

    def parse(self, file_path: Path, file_type: FileType) -> ParserResult:
        import fitz

        result = ParserResult(
            parser_name=self.name(),
            parser_version=self.version(),
            file_type=file_type,
        )

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            result.errors.append(f"Failed to open PDF: {e}")
            return result

        result.page_count = len(doc)
        result.metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "page_count": len(doc),
        }

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_data = self._extract_page(page, page_idx + 1, result)
            result.pages.append(page_data)

        doc.close()
        return result

    def _extract_page(
        self, page: Any, page_number: int, result: ParserResult
    ) -> dict[str, Any]:
        page_data: dict[str, Any] = {
            "page_number": page_number,
            "width": page.rect.width,
            "height": page.rect.height,
            "rotation": page.rotation,
            "text_blocks": [],
            "tables": [],
            "figures": [],
            "ocr_used": False,
        }

        # Extract text blocks using "dict" mode for layout info
        try:
            blocks = page.get_text("dict", flags=11)["blocks"]
            reading_order = 0
            for block in blocks:
                if block.get("type") == 0:  # text block
                    text = ""
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text += span.get("text", "")
                        text += "\n"
                    text = text.strip()
                    if not text:
                        continue

                    bbox = block.get("bbox", (0, 0, 0, 0))
                    block_type = self._classify_block(text, bbox, page)
                    font_size = self._get_dominant_font_size(block)

                    tb_data = {
                        "page_number": page_number,
                        "text": text,
                        "block_type": block_type,
                        "bounding_box": {
                            "x0": bbox[0],
                            "y0": bbox[1],
                            "x1": bbox[2],
                            "y1": bbox[3],
                        },
                        "reading_order_index": reading_order,
                        "font_size": font_size,
                        "confidence": 1.0,
                    }
                    page_data["text_blocks"].append(tb_data)
                    result.text_blocks.append(tb_data)
                    reading_order += 1
                elif block.get("type") == 1:  # image block
                    bbox = block.get("bbox", (0, 0, 0, 0))
                    fig_data = {
                        "page_number": page_number,
                        "figure_type": "image",
                        "bounding_box": {
                            "x0": bbox[0],
                            "y0": bbox[1],
                            "x1": bbox[2],
                            "y1": bbox[3],
                        },
                    }
                    page_data["figures"].append(fig_data)
                    result.figures.append(fig_data)
        except Exception as e:
            result.warnings.append(
                ParserWarning(
                    code="TEXT_EXTRACTION_ERROR",
                    message=f"Failed to extract text from page {page_number}: {e}",
                    page=page_number,
                )
            )

        # Check if page has very little text (might be scanned)
        total_text = " ".join(tb["text"] for tb in page_data["text_blocks"])
        if len(total_text.strip()) < 20 and page.rect.width > 100:
            result.warnings.append(
                ParserWarning(
                    code="POSSIBLY_SCANNED",
                    message=f"Page {page_number} has very little text. It may be scanned/image-based.",
                    page=page_number,
                )
            )

        # Extract tables
        try:
            tabs = page.find_tables()
            for tab_idx, tab in enumerate(tabs.tables):
                table_data = self._extract_table(tab, page_number, tab_idx)
                page_data["tables"].append(table_data)
                result.tables.append(table_data)
        except Exception as e:
            result.warnings.append(
                ParserWarning(
                    code="TABLE_EXTRACTION_ERROR",
                    message=f"Failed to extract tables from page {page_number}: {e}",
                    page=page_number,
                )
            )

        return page_data

    def _extract_table(
        self, tab: Any, page_number: int, tab_idx: int
    ) -> dict[str, Any]:
        extracted = tab.extract()
        cells = []
        for row_idx, row in enumerate(extracted):
            for col_idx, cell_val in enumerate(row):
                cells.append({
                    "row_index": row_idx,
                    "column_index": col_idx,
                    "value": str(cell_val) if cell_val is not None else "",
                    "data_type": "string",
                })

        bbox = tab.bbox
        return {
            "page_number": page_number,
            "title": None,
            "row_count": len(extracted),
            "column_count": len(extracted[0]) if extracted else 0,
            "cells": cells,
            "bounding_box": {
                "x0": bbox[0],
                "y0": bbox[1],
                "x1": bbox[2],
                "y1": bbox[3],
            } if bbox else None,
            "confidence": 0.9,
        }

    def _classify_block(
        self, text: str, bbox: tuple[float, ...], page: Any
    ) -> str:
        page_height = page.rect.height
        y_center = (bbox[1] + bbox[3]) / 2

        if y_center < page_height * 0.08:
            return "header"
        if y_center > page_height * 0.92:
            return "footer"
        return "paragraph"

    def _get_dominant_font_size(self, block: dict[str, Any]) -> float:
        sizes: list[float] = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sizes.append(span.get("size", 12.0))
        return max(set(sizes), key=sizes.count) if sizes else 12.0
