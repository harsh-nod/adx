"""Tests for DocumentGraph.to_markdown() and markdown export endpoints."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from adx.client import ADX
from adx.models.document import (
    Document,
    DocumentGraph,
    FileType,
    Page,
    Section,
    Sheet,
    Table,
    TableCell,
    TextBlock,
    TextBlockType,
    Workbook,
)

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def _make_graph(
    filename="test.pdf",
    pages=None,
    sections=None,
    workbook=None,
    file_type=FileType.PDF,
):
    doc = Document(filename=filename, file_type=file_type)
    return DocumentGraph(
        document=doc,
        pages=pages or [],
        sections=sections or [],
        workbook=workbook,
    )


class TestMarkdownHeadings:
    def test_heading_renders_with_hashes(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="Main Title", block_type=TextBlockType.HEADING, reading_order_index=0),
            ],
        )
        section = Section(title="Main Title", heading_level=1)
        graph = _make_graph(pages=[page], sections=[section])
        md = graph.to_markdown()
        assert "## Main Title" in md

    def test_heading_level_2(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="Sub Section", block_type=TextBlockType.HEADING, reading_order_index=0),
            ],
        )
        section = Section(title="Sub Section", heading_level=2)
        graph = _make_graph(pages=[page], sections=[section])
        md = graph.to_markdown()
        assert "### Sub Section" in md

    def test_heading_level_3(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="Deep", block_type=TextBlockType.HEADING, reading_order_index=0),
            ],
        )
        section = Section(title="Deep", heading_level=3)
        graph = _make_graph(pages=[page], sections=[section])
        md = graph.to_markdown()
        assert "#### Deep" in md

    def test_heading_without_section_defaults_to_level_2(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="Orphan Heading", block_type=TextBlockType.HEADING, reading_order_index=0),
            ],
        )
        graph = _make_graph(pages=[page])
        md = graph.to_markdown()
        assert "### Orphan Heading" in md


class TestMarkdownParagraphs:
    def test_paragraph_renders_as_text(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="Hello world", block_type=TextBlockType.PARAGRAPH, reading_order_index=0),
            ],
        )
        graph = _make_graph(pages=[page])
        md = graph.to_markdown()
        assert "Hello world" in md

    def test_multiple_paragraphs_in_order(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="First", block_type=TextBlockType.PARAGRAPH, reading_order_index=0),
                TextBlock(text="Second", block_type=TextBlockType.PARAGRAPH, reading_order_index=1),
            ],
        )
        graph = _make_graph(pages=[page])
        md = graph.to_markdown()
        assert md.index("First") < md.index("Second")


class TestMarkdownListItems:
    def test_list_item_renders_with_dash(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="Item one", block_type=TextBlockType.LIST_ITEM, reading_order_index=0),
            ],
        )
        graph = _make_graph(pages=[page])
        md = graph.to_markdown()
        assert "- Item one" in md

    def test_multiple_list_items(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="A", block_type=TextBlockType.LIST_ITEM, reading_order_index=0),
                TextBlock(text="B", block_type=TextBlockType.LIST_ITEM, reading_order_index=1),
            ],
        )
        graph = _make_graph(pages=[page])
        md = graph.to_markdown()
        assert "- A" in md
        assert "- B" in md


class TestMarkdownTables:
    def test_table_renders_as_markdown_table(self):
        table = Table(
            row_count=2,
            column_count=2,
            cells=[
                TableCell(row_index=0, column_index=0, value="A"),
                TableCell(row_index=0, column_index=1, value="B"),
                TableCell(row_index=1, column_index=0, value="1"),
                TableCell(row_index=1, column_index=1, value="2"),
            ],
        )
        page = Page(page_number=1, tables=[table])
        graph = _make_graph(pages=[page])
        md = graph.to_markdown()
        assert "| A | B |" in md
        assert "| --- | --- |" in md
        assert "| 1 | 2 |" in md


class TestMarkdownFootnotes:
    def test_footnote_renders_as_blockquote(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="A note", block_type=TextBlockType.FOOTNOTE, reading_order_index=0),
            ],
        )
        graph = _make_graph(pages=[page])
        md = graph.to_markdown()
        assert "> *A note*" in md


class TestMarkdownHeaderFooter:
    def test_header_footer_skipped(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="Header text", block_type=TextBlockType.HEADER, reading_order_index=0),
                TextBlock(text="Footer text", block_type=TextBlockType.FOOTER, reading_order_index=1),
                TextBlock(text="Page 1", block_type=TextBlockType.PAGE_NUMBER, reading_order_index=2),
                TextBlock(text="Body text", block_type=TextBlockType.PARAGRAPH, reading_order_index=3),
            ],
        )
        graph = _make_graph(pages=[page])
        md = graph.to_markdown()
        assert "Header text" not in md
        assert "Footer text" not in md
        assert "Body text" in md


class TestMarkdownWorkbook:
    def test_workbook_sheet_renders(self):
        table = Table(
            sheet_name="Sheet1",
            row_count=2,
            column_count=2,
            cells=[
                TableCell(row_index=0, column_index=0, value="Col1"),
                TableCell(row_index=0, column_index=1, value="Col2"),
                TableCell(row_index=1, column_index=0, value="X"),
                TableCell(row_index=1, column_index=1, value="Y"),
            ],
        )
        sheet = Sheet(name="Sheet1", tables=[table])
        wb = Workbook(sheets=[sheet])
        graph = _make_graph(workbook=wb, file_type=FileType.XLSX)
        md = graph.to_markdown()
        assert "## Sheet: Sheet1" in md
        assert "| Col1 | Col2 |" in md

    def test_workbook_only_no_pages(self):
        table = Table(
            sheet_name="Data",
            row_count=1,
            column_count=1,
            cells=[TableCell(row_index=0, column_index=0, value="Only")],
        )
        sheet = Sheet(name="Data", tables=[table])
        wb = Workbook(sheets=[sheet])
        graph = _make_graph(workbook=wb, file_type=FileType.XLSX)
        md = graph.to_markdown()
        assert "## Sheet: Data" in md
        assert "| Only |" in md


class TestMarkdownEmptyGraph:
    def test_empty_graph(self):
        graph = _make_graph()
        md = graph.to_markdown()
        assert "# test.pdf" in md

    def test_empty_page(self):
        page = Page(page_number=1)
        graph = _make_graph(pages=[page])
        md = graph.to_markdown()
        assert "# test.pdf" in md


class TestMarkdownReadingOrder:
    def test_blocks_sorted_by_reading_order(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="Second", block_type=TextBlockType.PARAGRAPH, reading_order_index=1),
                TextBlock(text="First", block_type=TextBlockType.PARAGRAPH, reading_order_index=0),
            ],
        )
        graph = _make_graph(pages=[page])
        md = graph.to_markdown()
        assert md.index("First") < md.index("Second")

    def test_pages_sorted_by_page_number(self):
        pages = [
            Page(
                page_number=2,
                text_blocks=[TextBlock(text="Page2", block_type=TextBlockType.PARAGRAPH, reading_order_index=0)],
            ),
            Page(
                page_number=1,
                text_blocks=[TextBlock(text="Page1", block_type=TextBlockType.PARAGRAPH, reading_order_index=0)],
            ),
        ]
        graph = _make_graph(pages=pages)
        md = graph.to_markdown()
        assert md.index("Page1") < md.index("Page2")


class TestMarkdownMixedContent:
    def test_heading_paragraph_table_mix(self):
        table = Table(
            row_count=2,
            column_count=1,
            cells=[
                TableCell(row_index=0, column_index=0, value="H"),
                TableCell(row_index=1, column_index=0, value="V"),
            ],
        )
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="Title", block_type=TextBlockType.HEADING, reading_order_index=0),
                TextBlock(text="Body", block_type=TextBlockType.PARAGRAPH, reading_order_index=1),
            ],
            tables=[table],
        )
        section = Section(title="Title", heading_level=1)
        graph = _make_graph(pages=[page], sections=[section])
        md = graph.to_markdown()
        assert "## Title" in md
        assert "Body" in md
        assert "| H |" in md

    def test_section_hierarchy(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="L1", block_type=TextBlockType.HEADING, reading_order_index=0),
                TextBlock(text="L2", block_type=TextBlockType.HEADING, reading_order_index=1),
            ],
        )
        sections = [
            Section(title="L1", heading_level=1),
            Section(title="L2", heading_level=2),
        ]
        graph = _make_graph(pages=[page], sections=sections)
        md = graph.to_markdown()
        assert "## L1" in md
        assert "### L2" in md


class TestMarkdownClientIntegration:
    def test_client_to_markdown(self, tmp_path):
        # Create a DOCX and upload via client
        docx_path = FIXTURE_DIR / "docx" / "sample.docx"
        if not docx_path.exists():
            pytest.skip("DOCX fixture not available")

        client = ADX(storage_dir=tmp_path)
        graph = client.upload(docx_path)
        md = client.to_markdown(graph.document.id)
        assert isinstance(md, str)
        assert len(md) > 0
        assert "# sample.docx" in md

    def test_client_to_markdown_not_found(self, tmp_path):
        client = ADX(storage_dir=tmp_path)
        with pytest.raises(ValueError, match="not found"):
            client.to_markdown("nonexistent")
