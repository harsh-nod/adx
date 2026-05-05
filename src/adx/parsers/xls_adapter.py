"""XLS (legacy Excel) parser adapter using xlrd."""

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

_HAS_XLRD = False
try:
    import xlrd
    _HAS_XLRD = True
except ImportError:
    pass


class XlrdAdapter(ParserAdapter):
    """Parser adapter for legacy .xls files using xlrd."""

    def name(self) -> str:
        return "xlrd"

    def version(self) -> str:
        if not _HAS_XLRD:
            return "not installed"
        import xlrd
        return getattr(xlrd, "__VERSION__", getattr(xlrd, "__version__", "unknown"))

    def capabilities(self) -> ParserCapabilities:
        return ParserCapabilities(
            supported_types=[FileType.XLS] if _HAS_XLRD else [],
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

        if not _HAS_XLRD:
            result.errors.append("xlrd is not installed. Run: pip install xlrd")
            return result

        import xlrd

        try:
            wb = xlrd.open_workbook(str(file_path))
        except Exception as e:
            result.errors.append(f"Failed to open XLS: {e}")
            return result

        result.sheet_count = wb.nsheets

        for sheet_idx in range(wb.nsheets):
            sheet = wb.sheet_by_index(sheet_idx)
            cells_data: list[dict[str, Any]] = []

            for row_idx in range(min(sheet.nrows, 500)):
                for col_idx in range(sheet.ncols):
                    cell = sheet.cell(row_idx, col_idx)
                    if cell.value is None or (isinstance(cell.value, str) and not cell.value.strip()):
                        continue

                    # Map xlrd cell types
                    data_type = "string"
                    value = cell.value
                    if cell.ctype == xlrd.XL_CELL_NUMBER:
                        data_type = "number"
                    elif cell.ctype == xlrd.XL_CELL_DATE:
                        data_type = "date"
                        try:
                            date_tuple = xlrd.xldate_as_tuple(cell.value, wb.datemode)
                            value = f"{date_tuple[0]:04d}-{date_tuple[1]:02d}-{date_tuple[2]:02d}"
                        except Exception:
                            pass
                    elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                        data_type = "boolean"
                        value = bool(cell.value)

                    cells_data.append({
                        "row": row_idx + 1,
                        "column": col_idx + 1,
                        "value": str(value) if not isinstance(value, str) else value,
                        "data_type": data_type,
                        "address": f"{chr(65 + col_idx)}{row_idx + 1}" if col_idx < 26 else None,
                    })

            sheet_data: dict[str, Any] = {
                "name": sheet.name,
                "index": sheet_idx,
                "is_visible": sheet.visibility == 0,
                "row_count": sheet.nrows,
                "column_count": sheet.ncols,
                "cells": cells_data,
                "formulas": [],
                "merged_cells": [],
                "hidden_rows": [],
                "hidden_columns": [],
                "comments": [],
            }

            if sheet.nrows > 500:
                result.warnings.append(ParserWarning(
                    code="TRUNCATED_SHEET",
                    message=f"Sheet '{sheet.name}' truncated at 500 rows (has {sheet.nrows}).",
                    sheet=sheet.name,
                ))

            result.sheets.append(sheet_data)

        result.metadata = {
            "sheet_count": wb.nsheets,
            "sheet_names": wb.sheet_names(),
        }

        return result
