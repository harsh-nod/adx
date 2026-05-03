"""Core agent tools for document inspection.

All tools are read-only, deterministic, and return structured JSON-serializable dicts.
Every result includes citations where applicable.
"""

from __future__ import annotations

import re
from typing import Any

from docunav.models.document import (
    Citation,
    CitationType,
    DocumentGraph,
    DocumentType,
    FileType,
    Formula,
    Sheet,
    Table,
    TextBlockType,
)


class DocumentInspector:
    """Provides agent-facing tools over a DocumentGraph.

    Usage:
        graph = ...  # loaded or built DocumentGraph
        inspector = DocumentInspector(graph)
        profile = inspector.profile_document()
        structure = inspector.list_structure()
    """

    def __init__(self, graph: DocumentGraph) -> None:
        self.graph = graph

    # ------------------------------------------------------------------
    # Tool 1: profile_document
    # ------------------------------------------------------------------

    def profile_document(self) -> dict[str, Any]:
        """Quick overview of the document — what is inside, what to inspect next."""
        doc = self.graph.document
        has_formulas = False
        has_hidden_sheets = False
        has_tables = bool(self.graph.get_all_tables())
        has_images = any(fig for p in self.graph.pages for fig in p.figures)
        has_scanned = any(p.ocr_used for p in self.graph.pages)

        if self.graph.workbook:
            has_formulas = any(
                f for s in self.graph.workbook.sheets for f in s.formulas
            )
            has_hidden_sheets = any(
                not s.is_visible for s in self.graph.workbook.sheets
            )

        warnings = [w for w in doc.confidence_summary.low_confidence_regions]

        if has_hidden_sheets:
            warnings.append("Workbook contains hidden sheets.")
        if self.graph.workbook and self.graph.workbook.external_links:
            warnings.append(
                f"Workbook references {len(self.graph.workbook.external_links)} external file(s)."
            )

        recommended = self._recommend_tools()

        return {
            "file_id": doc.id,
            "filename": doc.filename,
            "type": doc.file_type.value,
            "likely_document_types": [dt.value for dt in doc.likely_document_types],
            "page_count": doc.page_count,
            "sheet_count": doc.sheet_count,
            "language": self.graph.pages[0].detected_language if self.graph.pages else None,
            "has_scanned_pages": has_scanned,
            "has_tables": has_tables,
            "has_images": has_images,
            "has_formulas": has_formulas,
            "has_hidden_sheets": has_hidden_sheets,
            "has_low_confidence_regions": bool(doc.confidence_summary.low_confidence_regions),
            "confidence": doc.confidence_summary.overall,
            "warnings": warnings,
            "recommended_tools": recommended,
        }

    # ------------------------------------------------------------------
    # Tool 2: list_structure
    # ------------------------------------------------------------------

    def list_structure(self) -> dict[str, Any]:
        """Return the navigational structure of the document."""
        result: dict[str, Any] = {"file_id": self.graph.document.id}

        # Sections
        result["sections"] = [
            {
                "id": s.id,
                "title": s.title,
                "heading_level": s.heading_level,
                "start_page": s.start_page,
                "end_page": s.end_page,
                "parent_section_id": s.parent_section_id,
            }
            for s in self.graph.sections
        ]

        # Pages summary
        result["pages"] = [
            {
                "page_number": p.page_number,
                "text_block_count": len(p.text_blocks),
                "table_count": len(p.tables),
                "figure_count": len(p.figures),
                "ocr_used": p.ocr_used,
            }
            for p in self.graph.pages
        ]

        # Tables
        all_tables = self.graph.get_all_tables()
        result["tables"] = [
            {
                "id": t.id,
                "title": t.title,
                "page_number": t.page_number,
                "sheet_name": t.sheet_name,
                "rows": t.row_count,
                "columns": t.column_count,
            }
            for t in all_tables
        ]

        # Sheets
        if self.graph.workbook:
            result["sheets"] = [
                {
                    "name": s.name,
                    "index": s.index,
                    "visible": s.is_visible,
                    "used_range": s.used_range,
                    "formula_count": len(s.formulas),
                    "table_count": len(s.tables),
                    "hidden_rows": len(s.hidden_rows),
                    "hidden_columns": len(s.hidden_columns),
                }
                for s in self.graph.workbook.sheets
            ]

        return result

    # ------------------------------------------------------------------
    # Tool 3: search_document
    # ------------------------------------------------------------------

    def search_document(
        self,
        query: str,
        max_results: int = 20,
    ) -> dict[str, Any]:
        """Search document text and cells for a query string."""
        results: dict[str, Any] = {
            "file_id": self.graph.document.id,
            "query": query,
            "text_matches": [],
            "cell_matches": [],
            "table_matches": [],
        }

        # Text search
        text_hits = self.graph.search_text(query)
        for block, page_num in text_hits[:max_results]:
            results["text_matches"].append({
                "text": block.text[:500],
                "page_number": page_num,
                "block_type": block.block_type.value,
                "confidence": block.confidence,
                "citation": {"type": "page", "page_number": page_num},
            })

        # Cell search
        cell_hits = self.graph.search_cells(query)
        for cell in cell_hits[:max_results]:
            results["cell_matches"].append({
                "sheet_name": cell.sheet_name,
                "address": cell.address,
                "value": cell.value,
                "citation": {
                    "type": "cell",
                    "sheet_name": cell.sheet_name,
                    "cell_address": cell.address,
                },
            })

        # Table header search
        for table in self.graph.get_all_tables():
            if table.cells:
                header_row = [c for c in table.cells if c.row_index == 0]
                for cell in header_row:
                    if query.lower() in cell.value.lower():
                        results["table_matches"].append({
                            "table_id": table.id,
                            "title": table.title,
                            "page_number": table.page_number,
                            "sheet_name": table.sheet_name,
                            "matched_header": cell.value,
                        })
                        break

        return results

    # ------------------------------------------------------------------
    # Tool 4: get_page
    # ------------------------------------------------------------------

    def get_page(self, page_number: int) -> dict[str, Any]:
        """Inspect a specific page of a PDF/document."""
        page = self.graph.get_page(page_number)
        if page is None:
            return {"error": f"Page {page_number} not found.", "page_count": self.graph.document.page_count}

        return {
            "file_id": self.graph.document.id,
            "page_number": page.page_number,
            "width": page.width,
            "height": page.height,
            "text": page.full_text,
            "text_blocks": [
                {
                    "id": tb.id,
                    "text": tb.text,
                    "type": tb.block_type.value,
                    "bounding_box": tb.bounding_box.model_dump() if tb.bounding_box else None,
                    "confidence": tb.confidence,
                }
                for tb in page.text_blocks
            ],
            "tables": [
                {
                    "id": t.id,
                    "rows": t.row_count,
                    "columns": t.column_count,
                    "markdown": t.to_markdown(),
                    "title": t.title,
                }
                for t in page.tables
            ],
            "figures": [
                {
                    "id": f.id,
                    "type": f.figure_type,
                    "caption": f.caption,
                }
                for f in page.figures
            ],
            "ocr_used": page.ocr_used,
            "citation": {"type": "page", "page_number": page_number},
        }

    # ------------------------------------------------------------------
    # Tool 5: get_table
    # ------------------------------------------------------------------

    def get_table(self, table_id: str) -> dict[str, Any]:
        """Inspect a specific table by ID."""
        table = self.graph.get_table_by_id(table_id)
        if table is None:
            return {"error": f"Table {table_id} not found."}

        return {
            "file_id": self.graph.document.id,
            "table_id": table.id,
            "title": table.title,
            "page_number": table.page_number,
            "sheet_name": table.sheet_name,
            "rows": table.row_count,
            "columns": table.column_count,
            "data": table.to_rows(),
            "markdown": table.to_markdown(),
            "confidence": table.confidence,
            "warnings": [],
            "citation": {
                "type": "table",
                "page_number": table.page_number,
                "sheet_name": table.sheet_name,
            },
        }

    # ------------------------------------------------------------------
    # Tool 6: list_sheets
    # ------------------------------------------------------------------

    def list_sheets(self) -> dict[str, Any]:
        """List all sheets in a workbook with metadata."""
        if not self.graph.workbook:
            return {
                "file_id": self.graph.document.id,
                "error": "Not a spreadsheet file.",
            }

        return {
            "file_id": self.graph.document.id,
            "sheet_count": len(self.graph.workbook.sheets),
            "sheets": [
                {
                    "name": s.name,
                    "index": s.index,
                    "visible": s.is_visible,
                    "used_range": s.used_range,
                    "row_count": s.row_count,
                    "column_count": s.column_count,
                    "formula_count": len(s.formulas),
                    "table_count": len(s.tables),
                    "hidden_row_count": len(s.hidden_rows),
                    "hidden_column_count": len(s.hidden_columns),
                    "merged_cell_count": len(s.merged_cells),
                    "comment_count": len(s.comments),
                }
                for s in self.graph.workbook.sheets
            ],
            "named_ranges": self.graph.workbook.named_ranges,
            "external_links": self.graph.workbook.external_links,
        }

    # ------------------------------------------------------------------
    # Tool 7: read_range
    # ------------------------------------------------------------------

    def read_range(
        self,
        sheet_name: str,
        cell_range: str,
    ) -> dict[str, Any]:
        """Read a specific range from a spreadsheet sheet."""
        sheet = self.graph.get_sheet(sheet_name)
        if sheet is None:
            return {"error": f"Sheet '{sheet_name}' not found."}

        start, end = _parse_range(cell_range)
        if start is None or end is None:
            return {"error": f"Invalid range: {cell_range}"}

        result_cells: list[dict[str, Any]] = []
        for table in sheet.tables:
            for cell in table.cells:
                ref = cell.source_cell_ref
                if ref and _cell_in_range(ref, start, end):
                    # Find formula if exists
                    formula = None
                    for f in sheet.formulas:
                        if f.cell_address == ref:
                            formula = f.formula_text
                            break
                    result_cells.append({
                        "address": ref,
                        "value": cell.value,
                        "formula": formula,
                        "data_type": cell.data_type,
                        "is_hidden": _is_hidden_cell(ref, sheet),
                        "is_merged": cell.is_merged if hasattr(cell, "is_merged") else False,
                    })

        return {
            "file_id": self.graph.document.id,
            "sheet_name": sheet_name,
            "range": cell_range,
            "cells": result_cells,
            "citation": {
                "type": "cell_range",
                "sheet_name": sheet_name,
                "cell_range": cell_range,
            },
        }

    # ------------------------------------------------------------------
    # Tool 8: find_cells
    # ------------------------------------------------------------------

    def find_cells(
        self,
        query: str,
        sheet_name: str | None = None,
        max_results: int = 20,
    ) -> dict[str, Any]:
        """Find spreadsheet cells matching a query."""
        if not self.graph.workbook:
            return {"error": "Not a spreadsheet file."}

        matches: list[dict[str, Any]] = []
        query_lower = query.lower()

        sheets = self.graph.workbook.sheets
        if sheet_name:
            sheets = [s for s in sheets if s.name == sheet_name]

        for sheet in sheets:
            for table in sheet.tables:
                for cell in table.cells:
                    if query_lower in str(cell.value).lower():
                        # Get surrounding context (same row)
                        same_row = [
                            c for c in table.cells if c.row_index == cell.row_index
                        ]
                        context = {c.source_cell_ref or f"C{c.column_index}": c.value for c in same_row}

                        # Find formula
                        formula = None
                        for f in sheet.formulas:
                            if cell.source_cell_ref and f.cell_address == cell.source_cell_ref:
                                formula = f.formula_text
                                break

                        matches.append({
                            "sheet_name": sheet.name,
                            "address": cell.source_cell_ref or f"R{cell.row_index}C{cell.column_index}",
                            "value": cell.value,
                            "formula": formula,
                            "row_context": context,
                            "citation": {
                                "type": "cell",
                                "sheet_name": sheet.name,
                                "cell_address": cell.source_cell_ref,
                            },
                        })
                        if len(matches) >= max_results:
                            break

        return {
            "file_id": self.graph.document.id,
            "query": query,
            "matches": matches,
        }

    # ------------------------------------------------------------------
    # Tool 9: inspect_formula
    # ------------------------------------------------------------------

    def inspect_formula(
        self,
        sheet_name: str,
        cell_address: str,
    ) -> dict[str, Any]:
        """Inspect a formula in a specific cell."""
        if not self.graph.workbook:
            return {"error": "Not a spreadsheet file."}

        sheet = self.graph.get_sheet(sheet_name)
        if sheet is None:
            return {"error": f"Sheet '{sheet_name}' not found."}

        formula = None
        for f in sheet.formulas:
            if f.cell_address.upper() == cell_address.upper():
                formula = f
                break

        if formula is None:
            # Check if cell exists but has no formula
            for table in sheet.tables:
                for cell in table.cells:
                    if cell.source_cell_ref and cell.source_cell_ref.upper() == cell_address.upper():
                        return {
                            "file_id": self.graph.document.id,
                            "sheet_name": sheet_name,
                            "cell_address": cell_address,
                            "has_formula": False,
                            "value": cell.value,
                            "data_type": cell.data_type,
                        }
            return {"error": f"Cell {cell_address} not found in sheet '{sheet_name}'."}

        # Find dependents (cells that reference this cell)
        dependents: list[str] = []
        for f in sheet.formulas:
            if cell_address.upper() in [r.upper() for r in f.referenced_cells]:
                dependents.append(f.cell_address)

        warnings: list[str] = []
        if formula.external_references:
            warnings.append("Formula references external files.")
        if formula.referenced_sheets:
            other_sheets = [s for s in formula.referenced_sheets if s != sheet_name]
            if other_sheets:
                warnings.append(f"Formula references other sheets: {', '.join(other_sheets)}")

        return {
            "file_id": self.graph.document.id,
            "sheet_name": sheet_name,
            "cell_address": cell_address,
            "has_formula": True,
            "formula": formula.formula_text,
            "calculated_value": formula.calculated_value,
            "precedents": formula.referenced_cells,
            "precedent_ranges": formula.referenced_ranges,
            "referenced_sheets": formula.referenced_sheets,
            "dependents": dependents,
            "external_references": formula.external_references,
            "warnings": warnings,
            "citation": {
                "type": "formula",
                "sheet_name": sheet_name,
                "cell_address": cell_address,
                "text_snippet": formula.formula_text,
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recommend_tools(self) -> list[str]:
        tools: list[str] = []
        doc = self.graph.document

        if doc.file_type == FileType.PDF:
            tools.append("list_structure")
            if self.graph.get_all_tables():
                tools.append("get_table")
            tools.append("get_page")
            tools.append("search_document")

        if doc.file_type in (FileType.XLSX, FileType.XLS, FileType.CSV):
            tools.append("list_sheets")
            tools.append("read_range")
            tools.append("find_cells")
            if self.graph.workbook and any(
                f for s in self.graph.workbook.sheets for f in s.formulas
            ):
                tools.append("inspect_formula")

        tools.append("extract")
        return tools


# ---------------------------------------------------------------------------
# Range parsing utilities
# ---------------------------------------------------------------------------

_CELL_ADDR_RE = re.compile(r"^([A-Z]+)(\d+)$", re.IGNORECASE)


def _parse_cell(addr: str) -> tuple[int, int] | None:
    """Parse 'A1' -> (row=1, col=1)."""
    m = _CELL_ADDR_RE.match(addr.strip().replace("$", ""))
    if not m:
        return None
    col_str, row_str = m.group(1).upper(), m.group(2)
    col = 0
    for ch in col_str:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return int(row_str), col


def _parse_range(range_str: str) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """Parse 'A1:C10' -> ((1,1), (10,3))."""
    parts = range_str.split(":")
    if len(parts) != 2:
        return None, None
    return _parse_cell(parts[0]), _parse_cell(parts[1])


def _cell_in_range(
    cell_ref: str,
    start: tuple[int, int],
    end: tuple[int, int],
) -> bool:
    cell = _parse_cell(cell_ref)
    if cell is None:
        return False
    row, col = cell
    return start[0] <= row <= end[0] and start[1] <= col <= end[1]


def _is_hidden_cell(cell_ref: str, sheet: Sheet) -> bool:
    parsed = _parse_cell(cell_ref)
    if parsed is None:
        return False
    row, col = parsed
    return row in sheet.hidden_rows or col in sheet.hidden_columns
