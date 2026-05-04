"""Converts ParserResult into canonical DocumentGraph."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from adx.models.document import (
    BoundingBox,
    Citation,
    CitationType,
    ConfidenceSummary,
    Document,
    DocumentGraph,
    DocumentType,
    Figure,
    FileType,
    Formula,
    Page,
    ProcessingStatus,
    Section,
    Sheet,
    SpreadsheetCell,
    Table,
    TableCell,
    TextBlock,
    TextBlockType,
    Workbook,
)
from adx.parsers.base import ParserResult

logger = logging.getLogger(__name__)

BLOCK_TYPE_MAP = {
    "paragraph": TextBlockType.PARAGRAPH,
    "heading": TextBlockType.HEADING,
    "list_item": TextBlockType.LIST_ITEM,
    "caption": TextBlockType.CAPTION,
    "footnote": TextBlockType.FOOTNOTE,
    "header": TextBlockType.HEADER,
    "footer": TextBlockType.FOOTER,
    "page_number": TextBlockType.PAGE_NUMBER,
}


class GraphBuilder:
    """Builds a DocumentGraph from a ParserResult."""

    def build(
        self,
        result: ParserResult,
        file_path: Path,
        file_bytes: bytes | None = None,
    ) -> DocumentGraph:
        checksum = ""
        if file_bytes:
            checksum = Document.compute_checksum(file_bytes)

        doc = Document(
            filename=file_path.name,
            file_type=result.file_type,
            mime_type=_guess_mime(result.file_type),
            checksum=checksum,
            page_count=result.page_count,
            sheet_count=result.sheet_count,
            parser_used=result.parser_name,
            parser_version=result.parser_version,
            processing_status=(
                ProcessingStatus.COMPLETED if result.success else ProcessingStatus.FAILED
            ),
            metadata=result.metadata,
            likely_document_types=self._classify_document(result),
        )

        graph = DocumentGraph(document=doc)

        if result.file_type in (FileType.PDF, FileType.DOCX, FileType.RTF):
            self._build_pdf_graph(result, graph)
        elif result.file_type in (FileType.XLSX, FileType.XLS):
            self._build_excel_graph(result, graph)
        elif result.file_type == FileType.CSV:
            self._build_csv_graph(result, graph)

        # Compute confidence summary
        graph.document.confidence_summary = self._compute_confidence(graph, result)

        return graph

    def _build_pdf_graph(self, result: ParserResult, graph: DocumentGraph) -> None:
        heading_stack: list[Section] = []

        for page_data in result.pages:
            page = Page(
                page_number=page_data["page_number"],
                width=page_data.get("width", 0),
                height=page_data.get("height", 0),
                rotation=page_data.get("rotation", 0),
                ocr_used=page_data.get("ocr_used", False),
            )

            # Text blocks
            for tb_data in page_data.get("text_blocks", []):
                bbox = _make_bbox(tb_data.get("bounding_box"))
                block_type_str = tb_data.get("block_type", "paragraph")
                block_type = BLOCK_TYPE_MAP.get(block_type_str, TextBlockType.PARAGRAPH)

                # Detect headings by font size
                font_size = tb_data.get("font_size", 12.0)
                if font_size > 16 and block_type == TextBlockType.PARAGRAPH:
                    block_type = TextBlockType.HEADING

                tb = TextBlock(
                    page_number=page.page_number,
                    text=tb_data.get("text", ""),
                    block_type=block_type,
                    bounding_box=bbox,
                    reading_order_index=tb_data.get("reading_order_index", 0),
                    confidence=tb_data.get("confidence", 1.0),
                    source_parser=result.parser_name,
                )
                page.text_blocks.append(tb)

                # Build sections from headings
                if block_type == TextBlockType.HEADING:
                    level = 1 if font_size > 20 else 2 if font_size > 16 else 3
                    section = Section(
                        title=tb.text.strip(),
                        heading_level=level,
                        start_page=page.page_number,
                    )
                    # Pop stack to find parent
                    while heading_stack and heading_stack[-1].heading_level >= level:
                        heading_stack[-1].end_page = page.page_number
                        heading_stack.pop()
                    if heading_stack:
                        section.parent_section_id = heading_stack[-1].id
                    heading_stack.append(section)
                    graph.sections.append(section)

                # Create citation
                citation = Citation(
                    document_id=graph.document.id,
                    target_object_id=tb.id,
                    citation_type=CitationType.BOUNDING_BOX if bbox else CitationType.PAGE,
                    page_number=page.page_number,
                    bounding_box=bbox,
                    text_snippet=tb.text[:200],
                )
                graph.citations.append(citation)

            # Tables
            for tab_data in page_data.get("tables", []):
                table = _make_table(tab_data, result.parser_name)
                page.tables.append(table)
                graph.citations.append(Citation(
                    document_id=graph.document.id,
                    target_object_id=table.id,
                    citation_type=CitationType.TABLE,
                    page_number=page.page_number,
                    bounding_box=_make_bbox(tab_data.get("bounding_box")),
                ))

            # Figures
            for fig_data in page_data.get("figures", []):
                fig = Figure(
                    page_number=page.page_number,
                    figure_type=fig_data.get("figure_type", "image"),
                    caption=fig_data.get("caption"),
                    bounding_box=_make_bbox(fig_data.get("bounding_box")),
                )
                page.figures.append(fig)

            graph.pages.append(page)

        # Close remaining sections
        for sec in heading_stack:
            if sec.end_page is None:
                sec.end_page = result.page_count

    def _build_excel_graph(self, result: ParserResult, graph: DocumentGraph) -> None:
        workbook = Workbook(
            named_ranges=result.named_ranges,
            external_links=result.external_links,
        )

        for sheet_data in result.sheets:
            sheet = Sheet(
                name=sheet_data["name"],
                index=sheet_data.get("index", 0),
                is_visible=sheet_data.get("is_visible", True),
                used_range=sheet_data.get("used_range"),
                row_count=sheet_data.get("row_count", 0),
                column_count=sheet_data.get("column_count", 0),
                merged_cells=sheet_data.get("merged_cells", []),
                hidden_rows=sheet_data.get("hidden_rows", []),
                hidden_columns=sheet_data.get("hidden_columns", []),
                comments=sheet_data.get("comments", []),
            )

            # Formulas
            for f_data in sheet_data.get("formulas", []):
                formula = Formula(
                    sheet_name=f_data["sheet_name"],
                    cell_address=f_data["cell_address"],
                    formula_text=f_data["formula_text"],
                    referenced_cells=f_data.get("referenced_cells", []),
                    referenced_ranges=f_data.get("referenced_ranges", []),
                    referenced_sheets=f_data.get("referenced_sheets", []),
                    external_references=f_data.get("external_references", []),
                    calculated_value=f_data.get("calculated_value"),
                )
                sheet.formulas.append(formula)

            # Build a table from the sheet data
            cells_data = sheet_data.get("cells", [])
            if cells_data:
                table = self._cells_to_table(cells_data, sheet.name, result.parser_name)
                sheet.tables.append(table)

            workbook.sheets.append(sheet)

            # Create citations for each cell with a formula
            for formula in sheet.formulas:
                graph.citations.append(Citation(
                    document_id=graph.document.id,
                    target_object_id=formula.id,
                    citation_type=CitationType.FORMULA,
                    sheet_name=formula.sheet_name,
                    cell_address=formula.cell_address,
                    text_snippet=formula.formula_text[:200],
                ))

        graph.workbook = workbook

    def _build_csv_graph(self, result: ParserResult, graph: DocumentGraph) -> None:
        workbook = Workbook()

        for sheet_data in result.sheets:
            sheet = Sheet(
                name=sheet_data["name"],
                index=0,
                is_visible=True,
                used_range=sheet_data.get("used_range"),
                row_count=sheet_data.get("row_count", 0),
                column_count=sheet_data.get("column_count", 0),
            )

            for tab_data in result.tables:
                table = _make_table(tab_data, result.parser_name)
                sheet.tables.append(table)

            workbook.sheets.append(sheet)

        graph.workbook = workbook

    def _cells_to_table(
        self,
        cells: list[dict[str, Any]],
        sheet_name: str,
        parser_name: str,
    ) -> Table:
        max_row = max((c.get("row", c.get("row_index", 0)) for c in cells), default=0)
        max_col = max((c.get("column", c.get("column_index", 0)) for c in cells), default=0)

        # Normalize: openpyxl uses 1-based row/column
        table_cells: list[TableCell] = []
        for c in cells:
            row = c.get("row", c.get("row_index", 0))
            col = c.get("column", c.get("column_index", 0))
            # Convert to 0-based for Table model
            if row > 0:
                row -= 1
            if col > 0:
                col -= 1
            table_cells.append(TableCell(
                row_index=row,
                column_index=col,
                value=str(c.get("value", "")) if c.get("value") is not None else "",
                data_type=c.get("data_type", "string"),
                source_cell_ref=c.get("address"),
            ))

        return Table(
            sheet_name=sheet_name,
            row_count=max_row,
            column_count=max_col,
            cells=table_cells,
            confidence=1.0,
            source_parser=parser_name,
        )

    def _classify_document(self, result: ParserResult) -> list[DocumentType]:
        """Simple heuristic document type classification."""
        types: list[DocumentType] = []
        all_text = ""

        for tb in result.text_blocks:
            all_text += " " + tb.get("text", "")

        text_lower = all_text.lower()

        if result.file_type in (FileType.XLSX, FileType.XLS):
            types.append(DocumentType.SPREADSHEET)
            if any(
                kw in text_lower
                for kw in ["revenue", "ebitda", "forecast", "budget", "p&l", "profit"]
            ):
                types.append(DocumentType.FINANCIAL_MODEL)
        elif result.file_type == FileType.PDF:
            if any(kw in text_lower for kw in ["invoice", "bill to", "amount due", "total due"]):
                types.append(DocumentType.INVOICE)
            if any(
                kw in text_lower
                for kw in ["agreement", "contract", "whereas", "parties", "governing law"]
            ):
                types.append(DocumentType.CONTRACT)
            if any(kw in text_lower for kw in ["statement", "account", "balance", "transaction"]):
                types.append(DocumentType.BANK_STATEMENT)
            if any(kw in text_lower for kw in ["resume", "curriculum vitae", "experience", "education", "skills"]):
                types.append(DocumentType.RESUME)

        if not types:
            types.append(DocumentType.UNKNOWN)

        return types

    def _compute_confidence(
        self, graph: DocumentGraph, result: ParserResult
    ) -> ConfidenceSummary:
        text_confs: list[float] = []
        table_confs: list[float] = []
        ocr_confs: list[float] = []

        for page in graph.pages:
            for tb in page.text_blocks:
                text_confs.append(tb.confidence)
            for table in page.tables:
                table_confs.append(table.confidence)
            if page.ocr_used and page.ocr_confidence is not None:
                ocr_confs.append(page.ocr_confidence)

        low_regions: list[str] = []
        for w in result.warnings:
            if w.code in ("POSSIBLY_SCANNED", "HIDDEN_SHEET", "EXTERNAL_LINKS"):
                low_regions.append(w.message)

        return ConfidenceSummary(
            overall=_avg(text_confs + table_confs) if text_confs or table_confs else 1.0,
            text_confidence=_avg(text_confs) if text_confs else 1.0,
            table_confidence=_avg(table_confs) if table_confs else 1.0,
            ocr_confidence=_avg(ocr_confs) if ocr_confs else None,
            low_confidence_regions=low_regions,
        )


def _make_bbox(data: dict[str, Any] | None) -> BoundingBox | None:
    if not data:
        return None
    return BoundingBox(
        x0=data.get("x0", 0),
        y0=data.get("y0", 0),
        x1=data.get("x1", 0),
        y1=data.get("y1", 0),
    )


def _make_table(data: dict[str, Any], parser_name: str) -> Table:
    cells = [
        TableCell(
            row_index=c.get("row_index", 0),
            column_index=c.get("column_index", 0),
            value=str(c.get("value", "")) if c.get("value") is not None else "",
            data_type=c.get("data_type", "string"),
            source_cell_ref=c.get("address"),
        )
        for c in data.get("cells", [])
    ]
    return Table(
        page_number=data.get("page_number"),
        sheet_name=data.get("sheet_name"),
        title=data.get("title"),
        row_count=data.get("row_count", 0),
        column_count=data.get("column_count", 0),
        cells=cells,
        bounding_box=_make_bbox(data.get("bounding_box")),
        confidence=data.get("confidence", 1.0),
        source_parser=parser_name,
    )


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 1.0


def _guess_mime(ft: FileType) -> str:
    return {
        FileType.PDF: "application/pdf",
        FileType.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        FileType.XLS: "application/vnd.ms-excel",
        FileType.CSV: "text/csv",
        FileType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        FileType.RTF: "application/rtf",
        FileType.TEXT: "text/plain",
        FileType.IMAGE: "image/png",
    }.get(ft, "application/octet-stream")
