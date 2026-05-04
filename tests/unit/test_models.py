"""Tests for adx.models.document — DocumentGraph, Page, Table, Citation, etc."""

from __future__ import annotations

import hashlib
import json

import pytest

from adx.models.document import (
    BoundingBox,
    Citation,
    CitationType,
    ConfidenceSummary,
    Document,
    DocumentGraph,
    DocumentType,
    Extraction,
    ExtractionField,
    Figure,
    FileType,
    Formula,
    Page,
    ProcessingStatus,
    SCHEMA_VERSION,
    Section,
    Sheet,
    SpreadsheetCell,
    Table,
    TableCell,
    TextBlock,
    TextBlockType,
    ValidationResult,
    ValidationSeverity,
    Workbook,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_table_cells():
    """Create a 3x3 grid of cells with header row."""
    cells = []
    headers = ["Name", "Age", "City"]
    data = [["Alice", "30", "NYC"], ["Bob", "25", "LA"]]
    for col_idx, h in enumerate(headers):
        cells.append(TableCell(row_index=0, column_index=col_idx, value=h))
    for row_idx, row in enumerate(data, start=1):
        for col_idx, val in enumerate(row):
            cells.append(TableCell(row_index=row_idx, column_index=col_idx, value=val))
    return cells


@pytest.fixture
def sample_table(sample_table_cells):
    return Table(
        title="People",
        row_count=3,
        column_count=3,
        cells=sample_table_cells,
        page_number=1,
    )


@pytest.fixture
def sample_page(sample_table):
    tb1 = TextBlock(
        page_number=1,
        text="Introduction to the report.",
        block_type=TextBlockType.HEADING,
        reading_order_index=0,
    )
    tb2 = TextBlock(
        page_number=1,
        text="This report covers quarterly results.",
        block_type=TextBlockType.PARAGRAPH,
        reading_order_index=1,
    )
    fig = Figure(page_number=1, caption="Figure 1: Overview", figure_type="chart")
    return Page(
        page_number=1,
        width=612.0,
        height=792.0,
        text_blocks=[tb1, tb2],
        tables=[sample_table],
        figures=[fig],
    )


@pytest.fixture
def sample_workbook():
    cells = [
        TableCell(row_index=0, column_index=0, value="Revenue", source_cell_ref="A1"),
        TableCell(row_index=0, column_index=1, value="1000", source_cell_ref="B1"),
        TableCell(row_index=1, column_index=0, value="Cost", source_cell_ref="A2"),
        TableCell(row_index=1, column_index=1, value="600", source_cell_ref="B2"),
    ]
    table = Table(sheet_name="Summary", row_count=2, column_count=2, cells=cells)
    formula = Formula(
        sheet_name="Summary",
        cell_address="B3",
        formula_text="=B1-B2",
        referenced_cells=["B1", "B2"],
    )
    sheet = Sheet(
        name="Summary",
        index=0,
        is_visible=True,
        row_count=3,
        column_count=2,
        tables=[table],
        formulas=[formula],
    )
    hidden_sheet = Sheet(name="Hidden", index=1, is_visible=False, row_count=0, column_count=0)
    return Workbook(
        sheets=[sheet, hidden_sheet],
        named_ranges={"profit": "Summary!B3"},
        external_links=["other_file.xlsx"],
    )


@pytest.fixture
def sample_graph(sample_page, sample_workbook):
    doc = Document(
        filename="test.pdf",
        file_type=FileType.PDF,
        page_count=1,
        sheet_count=2,
        processing_status=ProcessingStatus.COMPLETED,
        likely_document_types=[DocumentType.REPORT],
    )
    section = Section(
        title="Introduction to the report.",
        heading_level=1,
        start_page=1,
        end_page=1,
    )
    return DocumentGraph(
        document=doc,
        pages=[sample_page],
        sections=[section],
        workbook=sample_workbook,
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_file_type_values(self):
        assert FileType.PDF.value == "pdf"
        assert FileType.CSV.value == "csv"
        assert FileType.UNKNOWN.value == "unknown"

    def test_processing_status_values(self):
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.COMPLETED.value == "completed"

    def test_document_type_values(self):
        assert DocumentType.INVOICE.value == "invoice"
        assert DocumentType.FINANCIAL_MODEL.value == "financial_model"

    def test_text_block_type_values(self):
        assert TextBlockType.HEADING.value == "heading"
        assert TextBlockType.PARAGRAPH.value == "paragraph"

    def test_citation_type_values(self):
        assert CitationType.TABLE.value == "table"
        assert CitationType.CELL.value == "cell"
        assert CitationType.FORMULA.value == "formula"

    def test_validation_severity_values(self):
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"


# ---------------------------------------------------------------------------
# BoundingBox
# ---------------------------------------------------------------------------

class TestBoundingBox:
    def test_width_and_height(self):
        bbox = BoundingBox(x0=10.0, y0=20.0, x1=110.0, y1=70.0)
        assert bbox.width == 100.0
        assert bbox.height == 50.0

    def test_zero_size_box(self):
        bbox = BoundingBox(x0=5.0, y0=5.0, x1=5.0, y1=5.0)
        assert bbox.width == 0.0
        assert bbox.height == 0.0

    def test_serialization_roundtrip(self):
        bbox = BoundingBox(x0=1.5, y0=2.5, x1=3.5, y1=4.5)
        data = bbox.model_dump()
        restored = BoundingBox.model_validate(data)
        assert restored == bbox


# ---------------------------------------------------------------------------
# TextBlock
# ---------------------------------------------------------------------------

class TestTextBlock:
    def test_defaults(self):
        tb = TextBlock()
        assert tb.text == ""
        assert tb.block_type == TextBlockType.PARAGRAPH
        assert tb.confidence == 1.0
        assert tb.page_number is None
        assert tb.bounding_box is None
        assert len(tb.id) == 16

    def test_with_bounding_box(self):
        bbox = BoundingBox(x0=0, y0=0, x1=100, y1=20)
        tb = TextBlock(text="Hello", bounding_box=bbox, page_number=1)
        assert tb.bounding_box.width == 100

    def test_unique_ids(self):
        a = TextBlock(text="A")
        b = TextBlock(text="B")
        assert a.id != b.id


# ---------------------------------------------------------------------------
# TableCell
# ---------------------------------------------------------------------------

class TestTableCell:
    def test_defaults(self):
        cell = TableCell()
        assert cell.row_index == 0
        assert cell.column_index == 0
        assert cell.value == ""
        assert cell.data_type == "string"
        assert cell.row_span == 1
        assert cell.column_span == 1

    def test_with_values(self):
        cell = TableCell(
            row_index=2,
            column_index=3,
            value="$100.00",
            data_type="currency",
            source_cell_ref="D3",
        )
        assert cell.value == "$100.00"
        assert cell.source_cell_ref == "D3"


# ---------------------------------------------------------------------------
# Table — to_rows() and to_markdown()
# ---------------------------------------------------------------------------

class TestTable:
    def test_to_rows(self, sample_table):
        rows = sample_table.to_rows()
        assert len(rows) == 3
        assert rows[0] == ["Name", "Age", "City"]
        assert rows[1] == ["Alice", "30", "NYC"]
        assert rows[2] == ["Bob", "25", "LA"]

    def test_to_rows_empty_table(self):
        table = Table(row_count=0, column_count=0)
        assert table.to_rows() == []

    def test_to_rows_cells_outside_bounds(self):
        """Cells with indices beyond row_count/column_count should be ignored."""
        cells = [
            TableCell(row_index=0, column_index=0, value="OK"),
            TableCell(row_index=5, column_index=5, value="Out of bounds"),
        ]
        table = Table(row_count=1, column_count=1, cells=cells)
        rows = table.to_rows()
        assert rows == [["OK"]]

    def test_to_markdown(self, sample_table):
        md = sample_table.to_markdown()
        lines = md.split("\n")
        assert len(lines) == 4  # header + separator + 2 data rows
        assert "Name" in lines[0]
        assert "---" in lines[1]
        assert "Alice" in lines[2]
        assert "Bob" in lines[3]

    def test_to_markdown_empty(self):
        table = Table(row_count=0, column_count=0)
        assert table.to_markdown() == ""

    def test_to_markdown_single_row(self):
        cells = [TableCell(row_index=0, column_index=0, value="Header")]
        table = Table(row_count=1, column_count=1, cells=cells)
        md = table.to_markdown()
        assert "Header" in md
        assert "---" in md

    def test_continued_table_links(self):
        t1 = Table(id="t1", continued_to_table_id="t2")
        t2 = Table(id="t2", continued_from_table_id="t1")
        assert t1.continued_to_table_id == t2.id
        assert t2.continued_from_table_id == t1.id


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

class TestPage:
    def test_full_text_sorted_by_reading_order(self):
        tb_b = TextBlock(text="Second", reading_order_index=1)
        tb_a = TextBlock(text="First", reading_order_index=0)
        page = Page(page_number=1, text_blocks=[tb_b, tb_a])
        assert page.full_text == "First\nSecond"

    def test_full_text_empty(self):
        page = Page(page_number=1)
        assert page.full_text == ""

    def test_page_defaults(self):
        page = Page()
        assert page.page_number == 0
        assert page.width == 0.0
        assert page.height == 0.0
        assert page.rotation == 0
        assert page.ocr_used is False
        assert page.ocr_confidence is None


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------

class TestSection:
    def test_section_defaults(self):
        section = Section(title="Intro")
        assert section.heading_level == 1
        assert section.parent_section_id is None
        assert section.text_block_ids == []


# ---------------------------------------------------------------------------
# Spreadsheet entities
# ---------------------------------------------------------------------------

class TestSpreadsheetCell:
    def test_defaults(self):
        cell = SpreadsheetCell()
        assert cell.sheet_name == ""
        assert cell.address == ""
        assert cell.value is None
        assert cell.formula is None
        assert cell.is_hidden is False

    def test_with_formula(self):
        cell = SpreadsheetCell(
            sheet_name="Sheet1",
            address="C5",
            value=400.0,
            formula="=A5+B5",
            data_type="number",
        )
        assert cell.formula == "=A5+B5"


class TestFormula:
    def test_defaults(self):
        f = Formula()
        assert f.formula_text == ""
        assert f.referenced_cells == []
        assert f.parse_status == "ok"

    def test_with_references(self):
        f = Formula(
            sheet_name="Sheet1",
            cell_address="D1",
            formula_text="=SUM(A1:C1)",
            referenced_ranges=["A1:C1"],
            calculated_value=300,
        )
        assert f.calculated_value == 300
        assert f.referenced_ranges == ["A1:C1"]


class TestSheet:
    def test_defaults(self):
        sheet = Sheet(name="Sheet1")
        assert sheet.is_visible is True
        assert sheet.tables == []
        assert sheet.formulas == []

    def test_hidden_sheet(self):
        sheet = Sheet(name="Hidden", is_visible=False, hidden_rows=[1, 3], hidden_columns=[2])
        assert not sheet.is_visible
        assert len(sheet.hidden_rows) == 2


class TestWorkbook:
    def test_defaults(self):
        wb = Workbook()
        assert wb.sheets == []
        assert wb.named_ranges == {}
        assert wb.external_links == []


# ---------------------------------------------------------------------------
# Citation
# ---------------------------------------------------------------------------

class TestCitation:
    def test_to_short_ref_page(self):
        c = Citation(page_number=5, citation_type=CitationType.PAGE)
        assert c.to_short_ref() == "page 5"

    def test_to_short_ref_cell(self):
        c = Citation(
            sheet_name="Revenue",
            cell_address="B2",
            citation_type=CitationType.CELL,
        )
        assert "sheet 'Revenue'" in c.to_short_ref()
        assert "cell B2" in c.to_short_ref()

    def test_to_short_ref_range(self):
        c = Citation(
            sheet_name="Data",
            cell_range="A1:D10",
            citation_type=CitationType.CELL_RANGE,
        )
        ref = c.to_short_ref()
        assert "range A1:D10" in ref

    def test_to_short_ref_unknown(self):
        c = Citation(citation_type=CitationType.PAGE)
        assert c.to_short_ref() == "unknown location"

    def test_to_short_ref_combined(self):
        c = Citation(
            page_number=2,
            sheet_name="Sheet1",
            cell_address="C3",
            cell_range="C1:C10",
        )
        ref = c.to_short_ref()
        assert "page 2" in ref
        assert "sheet 'Sheet1'" in ref
        assert "cell C3" in ref
        assert "range C1:C10" in ref


# ---------------------------------------------------------------------------
# Extraction and ValidationResult
# ---------------------------------------------------------------------------

class TestExtraction:
    def test_defaults(self):
        ex = Extraction(document_id="doc1")
        assert ex.document_id == "doc1"
        assert ex.status == "completed"
        assert ex.output == {}
        assert ex.fields == []
        assert ex.confidence == 1.0

    def test_with_fields(self):
        field = ExtractionField(
            field_path="total",
            value=100.0,
            confidence=0.9,
            citations=[Citation(page_number=1)],
        )
        ex = Extraction(document_id="doc1", fields=[field])
        assert len(ex.fields) == 1
        assert ex.fields[0].value == 100.0


class TestValidationResult:
    def test_defaults(self):
        vr = ValidationResult(
            extraction_id="ex1",
            severity=ValidationSeverity.ERROR,
            rule_name="test_rule",
            message="Something failed",
        )
        assert vr.status == "open"
        assert vr.affected_fields == []


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class TestDocument:
    def test_compute_checksum(self):
        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        assert Document.compute_checksum(data) == expected

    def test_defaults(self):
        doc = Document()
        assert doc.file_type == FileType.UNKNOWN
        assert doc.processing_status == ProcessingStatus.PENDING
        assert doc.metadata == {}
        assert doc.likely_document_types == []


# ---------------------------------------------------------------------------
# DocumentGraph — search and navigation methods
# ---------------------------------------------------------------------------

class TestDocumentGraph:
    def test_schema_version(self, sample_graph):
        assert sample_graph.schema_version == SCHEMA_VERSION

    def test_get_page_found(self, sample_graph):
        page = sample_graph.get_page(1)
        assert page is not None
        assert page.page_number == 1

    def test_get_page_not_found(self, sample_graph):
        assert sample_graph.get_page(99) is None

    def test_get_all_tables(self, sample_graph):
        tables = sample_graph.get_all_tables()
        # 1 table on page, 1 table in workbook sheet
        assert len(tables) >= 2

    def test_get_table_by_id(self, sample_graph):
        tables = sample_graph.get_all_tables()
        assert len(tables) > 0
        found = sample_graph.get_table_by_id(tables[0].id)
        assert found is not None
        assert found.id == tables[0].id

    def test_get_table_by_id_not_found(self, sample_graph):
        assert sample_graph.get_table_by_id("nonexistent") is None

    def test_get_all_text(self, sample_graph):
        text = sample_graph.get_all_text()
        assert "Introduction to the report" in text
        assert "quarterly results" in text

    def test_get_sheet_found(self, sample_graph):
        sheet = sample_graph.get_sheet("Summary")
        assert sheet is not None
        assert sheet.name == "Summary"

    def test_get_sheet_not_found(self, sample_graph):
        assert sample_graph.get_sheet("Nonexistent") is None

    def test_get_sheet_no_workbook(self):
        graph = DocumentGraph()
        assert graph.get_sheet("anything") is None

    def test_search_text(self, sample_graph):
        results = sample_graph.search_text("quarterly")
        assert len(results) == 1
        block, page_num = results[0]
        assert page_num == 1
        assert "quarterly" in block.text

    def test_search_text_case_insensitive(self, sample_graph):
        results = sample_graph.search_text("INTRODUCTION")
        assert len(results) == 1

    def test_search_text_no_match(self, sample_graph):
        results = sample_graph.search_text("nonexistent term xyz")
        assert len(results) == 0

    def test_search_cells(self, sample_graph):
        results = sample_graph.search_cells("Revenue")
        assert len(results) >= 1
        assert results[0].sheet_name == "Summary"

    def test_search_cells_case_insensitive(self, sample_graph):
        results = sample_graph.search_cells("revenue")
        assert len(results) >= 1

    def test_search_cells_no_workbook(self):
        graph = DocumentGraph()
        assert graph.search_cells("anything") == []

    def test_search_cells_no_match(self, sample_graph):
        results = sample_graph.search_cells("zzz_nonexistent_zzz")
        assert len(results) == 0

    # -- Serialization roundtrip --

    def test_serialization_roundtrip_json(self, sample_graph):
        json_str = sample_graph.model_dump_json()
        restored = DocumentGraph.model_validate_json(json_str)
        assert restored.document.filename == sample_graph.document.filename
        assert len(restored.pages) == len(sample_graph.pages)
        assert restored.schema_version == sample_graph.schema_version

    def test_serialization_roundtrip_dict(self, sample_graph):
        data = sample_graph.model_dump()
        restored = DocumentGraph.model_validate(data)
        assert restored.document.file_type == sample_graph.document.file_type
        # Verify nested structures survived
        assert len(restored.pages[0].text_blocks) == 2
        assert len(restored.pages[0].tables) == 1
        assert restored.workbook is not None
        assert len(restored.workbook.sheets) == 2

    def test_empty_graph_serialization(self):
        graph = DocumentGraph()
        data = json.loads(graph.model_dump_json())
        restored = DocumentGraph.model_validate(data)
        assert restored.pages == []
        assert restored.workbook is None


# ---------------------------------------------------------------------------
# ConfidenceSummary
# ---------------------------------------------------------------------------

class TestConfidenceSummary:
    def test_defaults(self):
        cs = ConfidenceSummary()
        assert cs.overall == 1.0
        assert cs.ocr_confidence is None
        assert cs.low_confidence_regions == []
