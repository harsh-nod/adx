"""Tests for GraphBuilder — building DocumentGraphs from ParserResults."""

from __future__ import annotations

from pathlib import Path

import pytest

from adx.models.document import (
    CitationType,
    DocumentType,
    FileType,
    ProcessingStatus,
    TextBlockType,
)
from adx.parsers.base import ParserResult, ParserWarning
from adx.parsers.graph_builder import GraphBuilder, _avg, _guess_mime, _make_bbox, _make_table


# ---------------------------------------------------------------------------
# Fixtures — mock ParserResults
# ---------------------------------------------------------------------------

@pytest.fixture
def builder():
    return GraphBuilder()


@pytest.fixture
def pdf_parser_result():
    """A ParserResult that mimics a 2-page PDF with text, tables, and figures."""
    return ParserResult(
        parser_name="pymupdf",
        parser_version="1.23.0",
        file_type=FileType.PDF,
        page_count=2,
        pages=[
            {
                "page_number": 1,
                "width": 612,
                "height": 792,
                "rotation": 0,
                "ocr_used": False,
                "text_blocks": [
                    {
                        "text": "Annual Report 2024",
                        "block_type": "heading",
                        "font_size": 24.0,
                        "reading_order_index": 0,
                        "confidence": 0.99,
                        "bounding_box": {"x0": 50, "y0": 50, "x1": 300, "y1": 80},
                    },
                    {
                        "text": "This document summarizes the annual financials.",
                        "block_type": "paragraph",
                        "font_size": 12.0,
                        "reading_order_index": 1,
                        "confidence": 0.95,
                    },
                ],
                "tables": [
                    {
                        "row_count": 2,
                        "column_count": 2,
                        "cells": [
                            {"row_index": 0, "column_index": 0, "value": "Metric"},
                            {"row_index": 0, "column_index": 1, "value": "Value"},
                            {"row_index": 1, "column_index": 0, "value": "Revenue"},
                            {"row_index": 1, "column_index": 1, "value": "1000000"},
                        ],
                        "bounding_box": {"x0": 50, "y0": 200, "x1": 400, "y1": 300},
                        "confidence": 0.92,
                    },
                ],
                "figures": [
                    {
                        "figure_type": "chart",
                        "caption": "Revenue over time",
                        "bounding_box": {"x0": 50, "y0": 400, "x1": 500, "y1": 700},
                    },
                ],
            },
            {
                "page_number": 2,
                "width": 612,
                "height": 792,
                "rotation": 0,
                "ocr_used": True,
                "text_blocks": [
                    {
                        "text": "Detailed Analysis",
                        "block_type": "paragraph",
                        "font_size": 18.0,
                        "reading_order_index": 0,
                        "confidence": 0.85,
                    },
                    {
                        "text": "Further details on cost structure are provided below.",
                        "block_type": "paragraph",
                        "font_size": 12.0,
                        "reading_order_index": 1,
                        "confidence": 0.80,
                    },
                ],
                "tables": [],
                "figures": [],
            },
        ],
        text_blocks=[
            {"text": "Annual Report 2024"},
            {"text": "This document summarizes the annual financials."},
        ],
        metadata={"author": "Test Corp"},
    )


@pytest.fixture
def csv_parser_result():
    """A ParserResult from a CSV parse."""
    cells = [
        {"row_index": 0, "column_index": 0, "value": "Product", "data_type": "string"},
        {"row_index": 0, "column_index": 1, "value": "Price", "data_type": "string"},
        {"row_index": 1, "column_index": 0, "value": "Widget", "data_type": "string"},
        {"row_index": 1, "column_index": 1, "value": "9.99", "data_type": "string"},
        {"row_index": 2, "column_index": 0, "value": "Gadget", "data_type": "string"},
        {"row_index": 2, "column_index": 1, "value": "19.99", "data_type": "string"},
    ]
    return ParserResult(
        parser_name="csv_stdlib",
        parser_version="3.11",
        file_type=FileType.CSV,
        sheet_count=1,
        tables=[
            {
                "page_number": None,
                "sheet_name": "Sheet1",
                "title": "products",
                "row_count": 3,
                "column_count": 2,
                "cells": cells,
                "confidence": 1.0,
            },
        ],
        sheets=[
            {
                "name": "Sheet1",
                "index": 0,
                "is_visible": True,
                "used_range": "A1:B3",
                "row_count": 3,
                "column_count": 2,
            },
        ],
    )


@pytest.fixture
def excel_parser_result():
    """A ParserResult from an Excel parse with formulas."""
    return ParserResult(
        parser_name="openpyxl",
        parser_version="3.1.0",
        file_type=FileType.XLSX,
        sheet_count=2,
        sheets=[
            {
                "name": "Income",
                "index": 0,
                "is_visible": True,
                "used_range": "A1:C5",
                "row_count": 5,
                "column_count": 3,
                "cells": [
                    {"row": 1, "column": 1, "value": "Revenue", "data_type": "string", "address": "A1"},
                    {"row": 1, "column": 2, "value": 50000, "data_type": "number", "address": "B1"},
                    {"row": 2, "column": 1, "value": "COGS", "data_type": "string", "address": "A2"},
                    {"row": 2, "column": 2, "value": 30000, "data_type": "number", "address": "B2"},
                    {"row": 3, "column": 1, "value": "Profit", "data_type": "string", "address": "A3"},
                    {"row": 3, "column": 2, "value": 20000, "data_type": "number", "address": "B3"},
                ],
                "formulas": [
                    {
                        "sheet_name": "Income",
                        "cell_address": "B3",
                        "formula_text": "=B1-B2",
                        "referenced_cells": ["B1", "B2"],
                        "referenced_ranges": [],
                        "referenced_sheets": [],
                        "external_references": [],
                        "calculated_value": 20000,
                    },
                ],
                "merged_cells": ["A5:C5"],
                "hidden_rows": [4],
                "hidden_columns": [],
                "comments": [{"cell": "A1", "text": "Main revenue line"}],
            },
            {
                "name": "Hidden",
                "index": 1,
                "is_visible": False,
                "used_range": "A1:A1",
                "row_count": 1,
                "column_count": 1,
                "cells": [
                    {"row": 1, "column": 1, "value": "secret", "data_type": "string", "address": "A1"},
                ],
                "formulas": [],
                "merged_cells": [],
                "hidden_rows": [],
                "hidden_columns": [],
                "comments": [],
            },
        ],
        named_ranges={"profit": "Income!B3"},
        external_links=["budget_2023.xlsx"],
        text_blocks=[
            {"text": "Revenue forecast and budget analysis"},
        ],
    )


@pytest.fixture
def failed_parser_result():
    return ParserResult(
        parser_name="pymupdf",
        parser_version="1.23.0",
        file_type=FileType.PDF,
        errors=["Failed to open file: corrupted"],
    )


# ---------------------------------------------------------------------------
# Build PDF graph
# ---------------------------------------------------------------------------

class TestBuildPDFGraph:
    def test_basic_structure(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        assert graph.document.filename == "report.pdf"
        assert graph.document.file_type == FileType.PDF
        assert graph.document.parser_used == "pymupdf"
        assert graph.document.processing_status == ProcessingStatus.COMPLETED
        assert graph.document.page_count == 2
        assert len(graph.pages) == 2

    def test_pages_populated(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        page1 = graph.get_page(1)
        assert page1 is not None
        assert page1.width == 612
        assert page1.height == 792
        assert len(page1.text_blocks) == 2
        assert len(page1.tables) == 1
        assert len(page1.figures) == 1

    def test_text_blocks_mapped(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        page1 = graph.get_page(1)
        heading_block = page1.text_blocks[0]
        assert heading_block.text == "Annual Report 2024"
        assert heading_block.block_type == TextBlockType.HEADING
        assert heading_block.confidence == 0.99
        assert heading_block.bounding_box is not None

    def test_heading_detection_by_font_size(self, builder, pdf_parser_result):
        """Font size > 16 for a paragraph should be promoted to heading."""
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        page2 = graph.get_page(2)
        # "Detailed Analysis" has font_size 18 and block_type "paragraph",
        # so it should be promoted to heading
        analysis_block = page2.text_blocks[0]
        assert analysis_block.block_type == TextBlockType.HEADING

    def test_tables_on_pages(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        page1 = graph.get_page(1)
        table = page1.tables[0]
        assert table.row_count == 2
        assert table.column_count == 2
        assert len(table.cells) == 4
        assert table.cells[0].value == "Metric"

    def test_figures_on_pages(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        page1 = graph.get_page(1)
        fig = page1.figures[0]
        assert fig.figure_type == "chart"
        assert fig.caption == "Revenue over time"
        assert fig.bounding_box is not None

    def test_sections_created_from_headings(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        # Should have at least 2 sections (one per heading)
        assert len(graph.sections) >= 2
        titles = [s.title for s in graph.sections]
        assert "Annual Report 2024" in titles

    def test_section_hierarchy(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        # "Annual Report 2024" (font_size=24) should be level 1
        # "Detailed Analysis" (font_size=18) should be level 2
        sec1 = next(s for s in graph.sections if s.title == "Annual Report 2024")
        sec2 = next(s for s in graph.sections if s.title == "Detailed Analysis")
        assert sec1.heading_level == 1
        assert sec2.heading_level == 2

    def test_citations_created(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        assert len(graph.citations) > 0
        # Should have citations for text blocks and tables
        text_citations = [c for c in graph.citations if c.citation_type in (CitationType.BOUNDING_BOX, CitationType.PAGE)]
        table_citations = [c for c in graph.citations if c.citation_type == CitationType.TABLE]
        assert len(text_citations) >= 2
        assert len(table_citations) >= 1

    def test_ocr_page_detected(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        page2 = graph.get_page(2)
        assert page2.ocr_used is True

    def test_checksum_computed(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"), file_bytes=b"test data")
        assert graph.document.checksum != ""
        assert len(graph.document.checksum) == 64  # SHA-256 hex

    def test_no_checksum_without_bytes(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        assert graph.document.checksum == ""

    def test_metadata_preserved(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        assert graph.document.metadata.get("author") == "Test Corp"


# ---------------------------------------------------------------------------
# Build CSV graph
# ---------------------------------------------------------------------------

class TestBuildCSVGraph:
    def test_basic_structure(self, builder, csv_parser_result):
        graph = builder.build(csv_parser_result, Path("products.csv"))
        assert graph.document.filename == "products.csv"
        assert graph.document.file_type == FileType.CSV
        assert graph.document.parser_used == "csv_stdlib"
        assert graph.workbook is not None

    def test_workbook_created(self, builder, csv_parser_result):
        graph = builder.build(csv_parser_result, Path("products.csv"))
        wb = graph.workbook
        assert len(wb.sheets) == 1
        assert wb.sheets[0].name == "Sheet1"

    def test_tables_in_sheet(self, builder, csv_parser_result):
        graph = builder.build(csv_parser_result, Path("products.csv"))
        sheet = wb_sheet = graph.workbook.sheets[0]
        assert len(sheet.tables) == 1
        table = sheet.tables[0]
        assert table.row_count == 3
        assert table.column_count == 2

    def test_cells_populated(self, builder, csv_parser_result):
        graph = builder.build(csv_parser_result, Path("products.csv"))
        table = graph.workbook.sheets[0].tables[0]
        assert len(table.cells) == 6
        values = [c.value for c in table.cells]
        assert "Product" in values
        assert "Widget" in values

    def test_no_pages_for_csv(self, builder, csv_parser_result):
        graph = builder.build(csv_parser_result, Path("products.csv"))
        assert len(graph.pages) == 0


# ---------------------------------------------------------------------------
# Build Excel graph
# ---------------------------------------------------------------------------

class TestBuildExcelGraph:
    def test_basic_structure(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        assert graph.document.file_type == FileType.XLSX
        assert graph.document.parser_used == "openpyxl"
        assert graph.workbook is not None

    def test_sheets_created(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        assert len(graph.workbook.sheets) == 2
        assert graph.workbook.sheets[0].name == "Income"
        assert graph.workbook.sheets[1].name == "Hidden"

    def test_hidden_sheet(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        hidden = graph.workbook.sheets[1]
        assert hidden.is_visible is False

    def test_formulas_mapped(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        income = graph.workbook.sheets[0]
        assert len(income.formulas) == 1
        f = income.formulas[0]
        assert f.formula_text == "=B1-B2"
        assert f.calculated_value == 20000
        assert "B1" in f.referenced_cells

    def test_formula_citations(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        formula_citations = [c for c in graph.citations if c.citation_type == CitationType.FORMULA]
        assert len(formula_citations) >= 1
        fc = formula_citations[0]
        assert fc.sheet_name == "Income"
        assert fc.cell_address == "B3"

    def test_named_ranges_preserved(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        assert graph.workbook.named_ranges == {"profit": "Income!B3"}

    def test_external_links_preserved(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        assert "budget_2023.xlsx" in graph.workbook.external_links

    def test_merged_cells_preserved(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        income = graph.workbook.sheets[0]
        assert "A5:C5" in income.merged_cells

    def test_hidden_rows_preserved(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        income = graph.workbook.sheets[0]
        assert 4 in income.hidden_rows

    def test_comments_preserved(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        income = graph.workbook.sheets[0]
        assert len(income.comments) == 1

    def test_cells_converted_to_table(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        income = graph.workbook.sheets[0]
        assert len(income.tables) == 1
        table = income.tables[0]
        assert len(table.cells) > 0


# ---------------------------------------------------------------------------
# Failed result
# ---------------------------------------------------------------------------

class TestFailedResult:
    def test_failed_status(self, builder, failed_parser_result):
        graph = builder.build(failed_parser_result, Path("bad.pdf"))
        assert graph.document.processing_status == ProcessingStatus.FAILED


# ---------------------------------------------------------------------------
# Document classification
# ---------------------------------------------------------------------------

class TestDocumentClassification:
    def test_spreadsheet_classification(self, builder, excel_parser_result):
        graph = builder.build(excel_parser_result, Path("model.xlsx"))
        types = graph.document.likely_document_types
        assert DocumentType.SPREADSHEET in types

    def test_financial_model_classification(self, builder):
        result = ParserResult(
            parser_name="openpyxl",
            parser_version="3.1.0",
            file_type=FileType.XLSX,
            sheet_count=1,
            sheets=[{
                "name": "Sheet1",
                "index": 0,
                "is_visible": True,
                "row_count": 0,
                "column_count": 0,
                "cells": [],
                "formulas": [],
                "merged_cells": [],
                "hidden_rows": [],
                "hidden_columns": [],
                "comments": [],
            }],
            text_blocks=[{"text": "Revenue forecast and EBITDA projections"}],
        )
        graph = builder.build(result, Path("model.xlsx"))
        assert DocumentType.FINANCIAL_MODEL in graph.document.likely_document_types

    def test_invoice_classification(self, builder):
        result = ParserResult(
            parser_name="pymupdf",
            parser_version="1.0",
            file_type=FileType.PDF,
            page_count=1,
            pages=[{
                "page_number": 1,
                "width": 612,
                "height": 792,
                "text_blocks": [{
                    "text": "Invoice #12345 - Amount Due: $500",
                    "font_size": 12.0,
                    "reading_order_index": 0,
                }],
                "tables": [],
                "figures": [],
            }],
            text_blocks=[{"text": "Invoice #12345 - Amount Due: $500"}],
        )
        graph = builder.build(result, Path("invoice.pdf"))
        assert DocumentType.INVOICE in graph.document.likely_document_types

    def test_unknown_classification(self, builder):
        result = ParserResult(
            parser_name="test",
            parser_version="1.0",
            file_type=FileType.TEXT,
            text_blocks=[{"text": "Just some random notes"}],
        )
        graph = builder.build(result, Path("notes.txt"))
        assert DocumentType.UNKNOWN in graph.document.likely_document_types


# ---------------------------------------------------------------------------
# Confidence computation
# ---------------------------------------------------------------------------

class TestConfidenceComputation:
    def test_confidence_computed(self, builder, pdf_parser_result):
        graph = builder.build(pdf_parser_result, Path("report.pdf"))
        cs = graph.document.confidence_summary
        assert 0.0 < cs.overall <= 1.0
        assert 0.0 < cs.text_confidence <= 1.0

    def test_low_confidence_warnings(self, builder):
        result = ParserResult(
            parser_name="test",
            parser_version="1.0",
            file_type=FileType.PDF,
            page_count=1,
            pages=[{
                "page_number": 1,
                "width": 612,
                "height": 792,
                "text_blocks": [],
                "tables": [],
                "figures": [],
            }],
            warnings=[
                ParserWarning(code="POSSIBLY_SCANNED", message="Page may be scanned."),
            ],
        )
        graph = builder.build(result, Path("scan.pdf"))
        assert "Page may be scanned." in graph.document.confidence_summary.low_confidence_regions


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    def test_make_bbox_none(self):
        assert _make_bbox(None) is None
        assert _make_bbox({}) is None

    def test_make_bbox_valid(self):
        bbox = _make_bbox({"x0": 10, "y0": 20, "x1": 30, "y1": 40})
        assert bbox is not None
        assert bbox.x0 == 10
        assert bbox.width == 20

    def test_make_table(self):
        data = {
            "page_number": 1,
            "sheet_name": None,
            "title": "Test Table",
            "row_count": 1,
            "column_count": 1,
            "cells": [{"row_index": 0, "column_index": 0, "value": "Hello"}],
            "confidence": 0.95,
        }
        table = _make_table(data, "test_parser")
        assert table.title == "Test Table"
        assert table.source_parser == "test_parser"
        assert len(table.cells) == 1

    def test_avg_empty(self):
        assert _avg([]) == 1.0

    def test_avg_values(self):
        assert _avg([0.8, 0.9, 1.0]) == pytest.approx(0.9)

    def test_guess_mime_pdf(self):
        assert _guess_mime(FileType.PDF) == "application/pdf"

    def test_guess_mime_csv(self):
        assert _guess_mime(FileType.CSV) == "text/csv"

    def test_guess_mime_unknown(self):
        assert _guess_mime(FileType.UNKNOWN) == "application/octet-stream"
