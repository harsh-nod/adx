"""CSV parser adapter."""

from __future__ import annotations

import csv
import io
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

MAX_ROWS = 100_000


class CSVAdapter(ParserAdapter):
    """Parser adapter for CSV files."""

    def name(self) -> str:
        return "csv_stdlib"

    def version(self) -> str:
        return "3.11"

    def capabilities(self) -> ParserCapabilities:
        return ParserCapabilities(
            supported_types=[FileType.CSV],
            extracts_text=True,
            extracts_tables=True,
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
            raw_bytes = file_path.read_bytes()
        except Exception as e:
            result.errors.append(f"Failed to read CSV: {e}")
            return result

        # Detect encoding
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw_bytes.decode("latin-1")
            except Exception as e:
                result.errors.append(f"Failed to decode CSV: {e}")
                return result

        # Detect dialect
        try:
            sample = text[:8192]
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel  # type: ignore[assignment]

        reader = csv.reader(io.StringIO(text), dialect)
        rows: list[list[str]] = []
        truncated = False

        for i, row in enumerate(reader):
            if i >= MAX_ROWS:
                truncated = True
                result.warnings.append(
                    ParserWarning(
                        code="TRUNCATED",
                        message=f"CSV exceeds {MAX_ROWS} rows. Truncated.",
                    )
                )
                break
            rows.append(row)

        if not rows:
            result.warnings.append(
                ParserWarning(code="EMPTY_CSV", message="CSV file is empty.")
            )
            return result

        col_count = max(len(r) for r in rows)
        cells: list[dict[str, Any]] = []
        for row_idx, row in enumerate(rows):
            for col_idx, val in enumerate(row):
                cells.append({
                    "row_index": row_idx,
                    "column_index": col_idx,
                    "value": val,
                    "data_type": "string",
                })

        table_data = {
            "page_number": None,
            "sheet_name": "Sheet1",
            "title": file_path.stem,
            "row_count": len(rows),
            "column_count": col_count,
            "cells": cells,
            "confidence": 1.0,
        }
        result.tables.append(table_data)

        result.sheet_count = 1
        result.sheets.append({
            "name": "Sheet1",
            "index": 0,
            "is_visible": True,
            "used_range": f"A1:{_col_letter(col_count)}{len(rows)}",
            "row_count": len(rows),
            "column_count": col_count,
            "cells": cells,
            "formulas": [],
            "merged_cells": [],
            "hidden_rows": [],
            "hidden_columns": [],
            "comments": [],
            "formula_count": 0,
        })

        result.metadata = {
            "row_count": len(rows),
            "column_count": col_count,
            "truncated": truncated,
        }

        return result


def _col_letter(n: int) -> str:
    """Convert 1-based column number to Excel-style letter."""
    s = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        s = chr(65 + remainder) + s
    return s or "A"
