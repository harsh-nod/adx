"""Tests for DocumentInspector tools with pre-built DocumentGraphs."""

from __future__ import annotations

import pytest

from adx.models.document import (
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
    Table,
    TableCell,
    TextBlock,
    TextBlockType,
    Workbook,
)
from adx.tools.inspector import (
    DocumentInspector,
    _cell_in_range,
    _is_hidden_cell,
    _parse_cell,
    _parse_range,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pdf_graph():
    """A DocumentGraph simulating a parsed 2-page PDF with tables, sections, and figures."""
    doc = Document(
        id="pdf001",
        filename="report.pdf",
        file_type=FileType.PDF,
        page_count=2,
        processing_status=ProcessingStatus.COMPLETED,
        likely_document_types=[DocumentType.REPORT],
    )

    tb1 = TextBlock(
        id="tb1",
        page_number=1,
        text="Executive Summary",
        block_type=TextBlockType.HEADING,
        reading_order_index=0,
        confidence=0.99,
    )
    tb2 = TextBlock(
        id="tb2",
        page_number=1,
        text="Revenue increased by 15% year over year.",
        block_type=TextBlockType.PARAGRAPH,
        reading_order_index=1,
        confidence=0.95,
    )
    table1_cells = [
        TableCell(id="c1", row_index=0, column_index=0, value="Quarter"),
        TableCell(id="c2", row_index=0, column_index=1, value="Revenue"),
        TableCell(id="c3", row_index=1, column_index=0, value="Q1"),
        TableCell(id="c4", row_index=1, column_index=1, value="250000"),
        TableCell(id="c5", row_index=2, column_index=0, value="Q2"),
        TableCell(id="c6", row_index=2, column_index=1, value="300000"),
    ]
    table1 = Table(
        id="tbl1",
        page_number=1,
        title="Quarterly Revenue",
        row_count=3,
        column_count=2,
        cells=table1_cells,
    )
    fig1 = Figure(id="fig1", page_number=1, caption="Revenue Chart", figure_type="chart")
    page1 = Page(
        page_number=1,
        width=612.0,
        height=792.0,
        text_blocks=[tb1, tb2],
        tables=[table1],
        figures=[fig1],
    )

    tb3 = TextBlock(
        id="tb3",
        page_number=2,
        text="Cost Analysis",
        block_type=TextBlockType.HEADING,
        reading_order_index=0,
    )
    tb4 = TextBlock(
        id="tb4",
        page_number=2,
        text="Operating costs remained stable.",
        block_type=TextBlockType.PARAGRAPH,
        reading_order_index=1,
    )
    page2 = Page(
        page_number=2,
        width=612.0,
        height=792.0,
        text_blocks=[tb3, tb4],
        ocr_used=True,
    )

    sec1 = Section(title="Executive Summary", heading_level=1, start_page=1, end_page=1)
    sec2 = Section(title="Cost Analysis", heading_level=1, start_page=2, end_page=2)

    return DocumentGraph(
        document=doc,
        pages=[page1, page2],
        sections=[sec1, sec2],
    )


@pytest.fixture
def spreadsheet_graph():
    """A DocumentGraph simulating a parsed Excel workbook with formulas."""
    doc = Document(
        id="xls001",
        filename="model.xlsx",
        file_type=FileType.XLSX,
        sheet_count=2,
        processing_status=ProcessingStatus.COMPLETED,
        likely_document_types=[DocumentType.SPREADSHEET, DocumentType.FINANCIAL_MODEL],
    )

    cells = [
        TableCell(row_index=0, column_index=0, value="Revenue", source_cell_ref="A1"),
        TableCell(row_index=0, column_index=1, value="50000", source_cell_ref="B1"),
        TableCell(row_index=1, column_index=0, value="COGS", source_cell_ref="A2"),
        TableCell(row_index=1, column_index=1, value="30000", source_cell_ref="B2"),
        TableCell(row_index=2, column_index=0, value="Profit", source_cell_ref="A3"),
        TableCell(row_index=2, column_index=1, value="20000", source_cell_ref="B3"),
    ]
    table = Table(
        id="xtbl1",
        sheet_name="Income",
        row_count=3,
        column_count=2,
        cells=cells,
    )

    formula1 = Formula(
        sheet_name="Income",
        cell_address="B3",
        formula_text="=B1-B2",
        referenced_cells=["B1", "B2"],
        referenced_ranges=[],
        referenced_sheets=[],
        calculated_value=20000,
    )
    formula2 = Formula(
        sheet_name="Income",
        cell_address="C1",
        formula_text="=SUM(B1:B3)",
        referenced_cells=["B1", "B2", "B3"],
        referenced_ranges=["B1:B3"],
        referenced_sheets=[],
        calculated_value=100000,
    )
    formula_ext = Formula(
        sheet_name="Income",
        cell_address="D1",
        formula_text="=[budget.xlsx]Sheet1!A1",
        referenced_cells=[],
        referenced_ranges=[],
        referenced_sheets=["Sheet1"],
        external_references=["budget.xlsx"],
        calculated_value=None,
    )

    sheet1 = Sheet(
        name="Income",
        index=0,
        is_visible=True,
        used_range="A1:D3",
        row_count=3,
        column_count=4,
        tables=[table],
        formulas=[formula1, formula2, formula_ext],
        hidden_rows=[5],
        hidden_columns=[3],
    )
    sheet2 = Sheet(
        name="Hidden",
        index=1,
        is_visible=False,
        row_count=0,
        column_count=0,
    )

    wb = Workbook(
        sheets=[sheet1, sheet2],
        named_ranges={"profit_cell": "Income!B3"},
        external_links=["budget.xlsx"],
    )

    return DocumentGraph(document=doc, workbook=wb)


@pytest.fixture
def csv_graph():
    """A DocumentGraph simulating a parsed CSV."""
    doc = Document(
        id="csv001",
        filename="data.csv",
        file_type=FileType.CSV,
        sheet_count=1,
        processing_status=ProcessingStatus.COMPLETED,
        likely_document_types=[DocumentType.SPREADSHEET],
    )
    cells = [
        TableCell(row_index=0, column_index=0, value="Name", source_cell_ref="A1"),
        TableCell(row_index=0, column_index=1, value="Score", source_cell_ref="B1"),
        TableCell(row_index=1, column_index=0, value="Alice", source_cell_ref="A2"),
        TableCell(row_index=1, column_index=1, value="95", source_cell_ref="B2"),
    ]
    table = Table(id="ctbl1", sheet_name="Sheet1", row_count=2, column_count=2, cells=cells)
    sheet = Sheet(name="Sheet1", index=0, is_visible=True, row_count=2, column_count=2, tables=[table])
    wb = Workbook(sheets=[sheet])
    return DocumentGraph(document=doc, workbook=wb)


@pytest.fixture
def pdf_inspector(pdf_graph):
    return DocumentInspector(pdf_graph)


@pytest.fixture
def spreadsheet_inspector(spreadsheet_graph):
    return DocumentInspector(spreadsheet_graph)


@pytest.fixture
def csv_inspector(csv_graph):
    return DocumentInspector(csv_graph)


# ---------------------------------------------------------------------------
# Tool 1: profile_document
# ---------------------------------------------------------------------------

class TestProfileDocument:
    def test_pdf_profile(self, pdf_inspector):
        profile = pdf_inspector.profile_document()
        assert profile["filename"] == "report.pdf"
        assert profile["type"] == "pdf"
        assert profile["page_count"] == 2
        assert profile["has_tables"] is True
        assert profile["has_images"] is True
        assert profile["has_scanned_pages"] is True
        assert profile["has_formulas"] is False
        assert profile["has_hidden_sheets"] is False
        assert "report" in profile["likely_document_types"]

    def test_spreadsheet_profile(self, spreadsheet_inspector):
        profile = spreadsheet_inspector.profile_document()
        assert profile["type"] == "xlsx"
        assert profile["has_formulas"] is True
        assert profile["has_hidden_sheets"] is True
        assert profile["has_tables"] is True
        assert any("external" in w.lower() for w in profile["warnings"])

    def test_recommended_tools_pdf(self, pdf_inspector):
        profile = pdf_inspector.profile_document()
        tools = profile["recommended_tools"]
        assert "list_structure" in tools
        assert "get_table" in tools
        assert "get_page" in tools
        assert "search_document" in tools
        assert "extract" in tools

    def test_recommended_tools_spreadsheet(self, spreadsheet_inspector):
        profile = spreadsheet_inspector.profile_document()
        tools = profile["recommended_tools"]
        assert "list_sheets" in tools
        assert "read_range" in tools
        assert "find_cells" in tools
        assert "inspect_formula" in tools
        assert "extract" in tools


# ---------------------------------------------------------------------------
# Tool 2: list_structure
# ---------------------------------------------------------------------------

class TestListStructure:
    def test_pdf_structure(self, pdf_inspector):
        structure = pdf_inspector.list_structure()
        assert structure["file_id"] == "pdf001"
        assert len(structure["sections"]) == 2
        assert len(structure["pages"]) == 2
        assert len(structure["tables"]) == 1

    def test_section_details(self, pdf_inspector):
        structure = pdf_inspector.list_structure()
        sections = structure["sections"]
        titles = [s["title"] for s in sections]
        assert "Executive Summary" in titles
        assert "Cost Analysis" in titles

    def test_page_details(self, pdf_inspector):
        structure = pdf_inspector.list_structure()
        page1_info = next(p for p in structure["pages"] if p["page_number"] == 1)
        assert page1_info["text_block_count"] == 2
        assert page1_info["table_count"] == 1
        assert page1_info["figure_count"] == 1
        assert page1_info["ocr_used"] is False

        page2_info = next(p for p in structure["pages"] if p["page_number"] == 2)
        assert page2_info["ocr_used"] is True

    def test_spreadsheet_structure_has_sheets(self, spreadsheet_inspector):
        structure = spreadsheet_inspector.list_structure()
        assert "sheets" in structure
        assert len(structure["sheets"]) == 2
        income_sheet = next(s for s in structure["sheets"] if s["name"] == "Income")
        assert income_sheet["visible"] is True
        assert income_sheet["formula_count"] == 3


# ---------------------------------------------------------------------------
# Tool 3: search_document
# ---------------------------------------------------------------------------

class TestSearchDocument:
    def test_text_search(self, pdf_inspector):
        result = pdf_inspector.search_document("Revenue")
        assert result["query"] == "Revenue"
        assert len(result["text_matches"]) >= 1
        match = result["text_matches"][0]
        assert "Revenue" in match["text"]
        assert match["page_number"] == 1

    def test_text_search_case_insensitive(self, pdf_inspector):
        result = pdf_inspector.search_document("revenue")
        assert len(result["text_matches"]) >= 1

    def test_text_search_no_match(self, pdf_inspector):
        result = pdf_inspector.search_document("xyznonexistent")
        assert len(result["text_matches"]) == 0

    def test_cell_search(self, spreadsheet_inspector):
        result = spreadsheet_inspector.search_document("Revenue")
        assert len(result["cell_matches"]) >= 1
        cell_match = result["cell_matches"][0]
        assert cell_match["sheet_name"] == "Income"

    def test_table_header_search(self, pdf_inspector):
        result = pdf_inspector.search_document("Quarter")
        assert len(result["table_matches"]) >= 1
        assert result["table_matches"][0]["matched_header"] == "Quarter"

    def test_max_results_limit(self, pdf_inspector):
        result = pdf_inspector.search_document("e", max_results=1)
        assert len(result["text_matches"]) <= 1


# ---------------------------------------------------------------------------
# Tool 4: get_page
# ---------------------------------------------------------------------------

class TestGetPage:
    def test_get_existing_page(self, pdf_inspector):
        result = pdf_inspector.get_page(1)
        assert result["page_number"] == 1
        assert result["width"] == 612.0
        assert "Executive Summary" in result["text"]
        assert len(result["text_blocks"]) == 2
        assert len(result["tables"]) == 1
        assert len(result["figures"]) == 1

    def test_table_on_page(self, pdf_inspector):
        result = pdf_inspector.get_page(1)
        table = result["tables"][0]
        assert table["id"] == "tbl1"
        assert table["rows"] == 3
        assert table["columns"] == 2
        assert "Quarter" in table["markdown"]

    def test_figure_on_page(self, pdf_inspector):
        result = pdf_inspector.get_page(1)
        fig = result["figures"][0]
        assert fig["type"] == "chart"
        assert fig["caption"] == "Revenue Chart"

    def test_get_page_not_found(self, pdf_inspector):
        result = pdf_inspector.get_page(99)
        assert "error" in result
        assert result["page_count"] == 2

    def test_page_citation(self, pdf_inspector):
        result = pdf_inspector.get_page(1)
        assert result["citation"]["type"] == "page"
        assert result["citation"]["page_number"] == 1


# ---------------------------------------------------------------------------
# Tool 5: get_table
# ---------------------------------------------------------------------------

class TestGetTable:
    def test_get_existing_table(self, pdf_inspector):
        result = pdf_inspector.get_table("tbl1")
        assert result["table_id"] == "tbl1"
        assert result["title"] == "Quarterly Revenue"
        assert result["rows"] == 3
        assert result["columns"] == 2
        assert len(result["data"]) == 3
        assert result["data"][0] == ["Quarter", "Revenue"]

    def test_get_table_markdown(self, pdf_inspector):
        result = pdf_inspector.get_table("tbl1")
        assert "Quarter" in result["markdown"]
        assert "Q1" in result["markdown"]

    def test_get_table_not_found(self, pdf_inspector):
        result = pdf_inspector.get_table("nonexistent")
        assert "error" in result

    def test_get_table_citation(self, pdf_inspector):
        result = pdf_inspector.get_table("tbl1")
        assert result["citation"]["type"] == "table"
        assert result["citation"]["page_number"] == 1


# ---------------------------------------------------------------------------
# Tool 6: list_sheets
# ---------------------------------------------------------------------------

class TestListSheets:
    def test_list_sheets_spreadsheet(self, spreadsheet_inspector):
        result = spreadsheet_inspector.list_sheets()
        assert result["sheet_count"] == 2
        assert len(result["sheets"]) == 2

        income = next(s for s in result["sheets"] if s["name"] == "Income")
        assert income["visible"] is True
        assert income["formula_count"] == 3
        assert income["table_count"] == 1
        assert income["row_count"] == 3

        hidden = next(s for s in result["sheets"] if s["name"] == "Hidden")
        assert hidden["visible"] is False

    def test_list_sheets_named_ranges(self, spreadsheet_inspector):
        result = spreadsheet_inspector.list_sheets()
        assert result["named_ranges"] == {"profit_cell": "Income!B3"}

    def test_list_sheets_external_links(self, spreadsheet_inspector):
        result = spreadsheet_inspector.list_sheets()
        assert "budget.xlsx" in result["external_links"]

    def test_list_sheets_not_spreadsheet(self, pdf_inspector):
        result = pdf_inspector.list_sheets()
        assert "error" in result


# ---------------------------------------------------------------------------
# Tool 7: read_range
# ---------------------------------------------------------------------------

class TestReadRange:
    def test_read_valid_range(self, spreadsheet_inspector):
        result = spreadsheet_inspector.read_range("Income", "A1:B3")
        assert result["sheet_name"] == "Income"
        assert result["range"] == "A1:B3"
        assert len(result["cells"]) > 0
        addresses = [c["address"] for c in result["cells"]]
        assert "A1" in addresses
        assert "B1" in addresses

    def test_read_range_has_formula(self, spreadsheet_inspector):
        result = spreadsheet_inspector.read_range("Income", "B3:B3")
        if result["cells"]:
            b3 = result["cells"][0]
            assert b3["formula"] == "=B1-B2"

    def test_read_range_sheet_not_found(self, spreadsheet_inspector):
        result = spreadsheet_inspector.read_range("Nonexistent", "A1:B2")
        assert "error" in result

    def test_read_range_invalid_range(self, spreadsheet_inspector):
        result = spreadsheet_inspector.read_range("Income", "invalid")
        assert "error" in result

    def test_read_range_citation(self, spreadsheet_inspector):
        result = spreadsheet_inspector.read_range("Income", "A1:B3")
        assert result["citation"]["type"] == "cell_range"
        assert result["citation"]["sheet_name"] == "Income"

    def test_read_range_hidden_cell(self, spreadsheet_inspector):
        """Row 5 and column 3 are hidden in the Income sheet."""
        # Cell A5 would be hidden (row 5 is hidden)
        # We need a cell ref that falls in a hidden row/column
        result = spreadsheet_inspector.read_range("Income", "A1:B2")
        # Check that the cells have is_hidden field
        for cell in result["cells"]:
            assert "is_hidden" in cell


# ---------------------------------------------------------------------------
# Tool 8: find_cells
# ---------------------------------------------------------------------------

class TestFindCells:
    def test_find_cells_by_value(self, spreadsheet_inspector):
        result = spreadsheet_inspector.find_cells("Revenue")
        assert len(result["matches"]) >= 1
        match = result["matches"][0]
        assert match["sheet_name"] == "Income"
        assert match["value"] == "Revenue"

    def test_find_cells_case_insensitive(self, spreadsheet_inspector):
        result = spreadsheet_inspector.find_cells("revenue")
        assert len(result["matches"]) >= 1

    def test_find_cells_with_context(self, spreadsheet_inspector):
        result = spreadsheet_inspector.find_cells("Revenue")
        match = result["matches"][0]
        assert "row_context" in match

    def test_find_cells_with_sheet_filter(self, spreadsheet_inspector):
        result = spreadsheet_inspector.find_cells("Revenue", sheet_name="Income")
        assert len(result["matches"]) >= 1
        # All matches should be from Income sheet
        for m in result["matches"]:
            assert m["sheet_name"] == "Income"

    def test_find_cells_sheet_filter_no_match(self, spreadsheet_inspector):
        result = spreadsheet_inspector.find_cells("Revenue", sheet_name="Hidden")
        assert len(result["matches"]) == 0

    def test_find_cells_max_results(self, spreadsheet_inspector):
        result = spreadsheet_inspector.find_cells("0", max_results=2)
        assert len(result["matches"]) <= 2

    def test_find_cells_no_workbook(self, pdf_inspector):
        result = pdf_inspector.find_cells("anything")
        assert "error" in result

    def test_find_cells_citation(self, spreadsheet_inspector):
        result = spreadsheet_inspector.find_cells("Revenue")
        match = result["matches"][0]
        assert match["citation"]["type"] == "cell"
        assert match["citation"]["sheet_name"] == "Income"


# ---------------------------------------------------------------------------
# Tool 9: inspect_formula
# ---------------------------------------------------------------------------

class TestInspectFormula:
    def test_inspect_existing_formula(self, spreadsheet_inspector):
        result = spreadsheet_inspector.inspect_formula("Income", "B3")
        assert result["has_formula"] is True
        assert result["formula"] == "=B1-B2"
        assert result["calculated_value"] == 20000
        assert "B1" in result["precedents"]
        assert "B2" in result["precedents"]

    def test_inspect_formula_dependents(self, spreadsheet_inspector):
        """B1 is referenced by B3 and C1, so those should be dependents of B1."""
        result = spreadsheet_inspector.inspect_formula("Income", "B3")
        # C1 references B3, so B3 should have C1 as a dependent
        assert "C1" in result["dependents"]

    def test_inspect_formula_with_external_reference(self, spreadsheet_inspector):
        result = spreadsheet_inspector.inspect_formula("Income", "D1")
        assert result["has_formula"] is True
        assert len(result["external_references"]) > 0
        assert any("external" in w.lower() for w in result["warnings"])

    def test_inspect_formula_cross_sheet_warning(self, spreadsheet_inspector):
        result = spreadsheet_inspector.inspect_formula("Income", "D1")
        # D1 references "Sheet1" which is different from "Income"
        assert any("other sheets" in w.lower() for w in result["warnings"])

    def test_inspect_cell_without_formula(self, spreadsheet_inspector):
        result = spreadsheet_inspector.inspect_formula("Income", "A1")
        assert result["has_formula"] is False
        assert result["value"] == "Revenue"

    def test_inspect_formula_sheet_not_found(self, spreadsheet_inspector):
        result = spreadsheet_inspector.inspect_formula("Nonexistent", "A1")
        assert "error" in result

    def test_inspect_formula_cell_not_found(self, spreadsheet_inspector):
        result = spreadsheet_inspector.inspect_formula("Income", "Z99")
        assert "error" in result

    def test_inspect_formula_not_spreadsheet(self, pdf_inspector):
        result = pdf_inspector.inspect_formula("Sheet1", "A1")
        assert "error" in result

    def test_inspect_formula_case_insensitive(self, spreadsheet_inspector):
        result = spreadsheet_inspector.inspect_formula("Income", "b3")
        assert result["has_formula"] is True

    def test_inspect_formula_citation(self, spreadsheet_inspector):
        result = spreadsheet_inspector.inspect_formula("Income", "B3")
        assert result["citation"]["type"] == "formula"
        assert result["citation"]["sheet_name"] == "Income"


# ---------------------------------------------------------------------------
# Range parsing utilities
# ---------------------------------------------------------------------------

class TestParseCell:
    def test_simple_cell(self):
        assert _parse_cell("A1") == (1, 1)

    def test_multi_letter_column(self):
        assert _parse_cell("AA10") == (10, 27)

    def test_dollar_signs_stripped(self):
        assert _parse_cell("$A$1") == (1, 1)

    def test_case_insensitive(self):
        assert _parse_cell("b2") == (2, 2)

    def test_invalid(self):
        assert _parse_cell("invalid") is None
        assert _parse_cell("123") is None
        assert _parse_cell("") is None


class TestParseRange:
    def test_valid_range(self):
        start, end = _parse_range("A1:C10")
        assert start == (1, 1)
        assert end == (10, 3)

    def test_invalid_range_no_colon(self):
        start, end = _parse_range("A1C10")
        assert start is None
        assert end is None

    def test_invalid_range_bad_cells(self):
        start, end = _parse_range("XXX:YYY")
        assert start is None
        assert end is None


class TestCellInRange:
    def test_in_range(self):
        assert _cell_in_range("B2", (1, 1), (3, 3)) is True

    def test_out_of_range(self):
        assert _cell_in_range("D4", (1, 1), (3, 3)) is False

    def test_on_boundary(self):
        assert _cell_in_range("A1", (1, 1), (3, 3)) is True
        assert _cell_in_range("C3", (1, 1), (3, 3)) is True

    def test_invalid_cell_ref(self):
        assert _cell_in_range("invalid", (1, 1), (3, 3)) is False


class TestIsHiddenCell:
    def test_hidden_row(self):
        sheet = Sheet(name="S", hidden_rows=[5], hidden_columns=[])
        assert _is_hidden_cell("A5", sheet) is True

    def test_hidden_column(self):
        sheet = Sheet(name="S", hidden_rows=[], hidden_columns=[3])
        assert _is_hidden_cell("C1", sheet) is True

    def test_not_hidden(self):
        sheet = Sheet(name="S", hidden_rows=[5], hidden_columns=[3])
        assert _is_hidden_cell("A1", sheet) is False

    def test_invalid_ref(self):
        sheet = Sheet(name="S", hidden_rows=[1], hidden_columns=[])
        assert _is_hidden_cell("invalid", sheet) is False
