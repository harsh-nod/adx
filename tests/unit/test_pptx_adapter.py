"""Tests for the PPTX parser adapter."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from adx.models.document import DocumentType, FileType
from adx.parsers.graph_builder import GraphBuilder
from adx.parsers.pptx_adapter import PptxAdapter
from adx.parsers.registry import ParserRegistry

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "pptx"


@pytest.fixture(scope="module", autouse=True)
def ensure_fixture():
    """Generate the PPTX fixture if it doesn't exist."""
    sample = FIXTURE_DIR / "sample.pptx"
    if not sample.exists():
        script = Path(__file__).parent.parent / "fixtures" / "create_pptx_fixture.py"
        subprocess.run([sys.executable, str(script)], check=True)
    return sample


@pytest.fixture
def adapter():
    return PptxAdapter()


@pytest.fixture
def sample_pptx():
    return FIXTURE_DIR / "sample.pptx"


class TestPptxAdapterCapabilities:
    def test_name(self, adapter):
        assert adapter.name() == "python-pptx"

    def test_version_returns_string(self, adapter):
        assert isinstance(adapter.version(), str)

    def test_supports_pptx(self, adapter):
        assert adapter.supports(FileType.PPTX)

    def test_does_not_support_pdf(self, adapter):
        assert not adapter.supports(FileType.PDF)

    def test_does_not_support_docx(self, adapter):
        assert not adapter.supports(FileType.DOCX)

    def test_capabilities_text(self, adapter):
        caps = adapter.capabilities()
        assert caps.extracts_text is True

    def test_capabilities_tables(self, adapter):
        caps = adapter.capabilities()
        assert caps.extracts_tables is True


class TestPptxParsing:
    def test_parse_returns_result(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        assert result.success
        assert result.file_type == FileType.PPTX

    def test_slide_count(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        assert result.page_count == 3

    def test_pages_match_slides(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        assert len(result.pages) == 3

    def test_slide_page_numbers(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        page_nums = [p["page_number"] for p in result.pages]
        assert page_nums == [1, 2, 3]

    def test_title_extracted_as_heading(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        slide1_blocks = result.pages[0]["text_blocks"]
        headings = [b for b in slide1_blocks if b["block_type"] == "heading"]
        assert len(headings) >= 1
        assert "Test Presentation Title" in headings[0]["text"]

    def test_heading_font_size(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        slide1_blocks = result.pages[0]["text_blocks"]
        headings = [b for b in slide1_blocks if b["block_type"] == "heading"]
        assert headings[0]["font_size"] == 24.0

    def test_body_text_extracted(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        slide2_blocks = result.pages[1]["text_blocks"]
        texts = [b["text"] for b in slide2_blocks if b["block_type"] == "paragraph"]
        assert any("bullet point" in t for t in texts)

    def test_table_extraction(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        # Slide 3 has a table
        slide3_tables = result.pages[2]["tables"]
        assert len(slide3_tables) == 1
        table = slide3_tables[0]
        assert table["row_count"] == 4
        assert table["column_count"] == 3

    def test_table_cell_values(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        table = result.pages[2]["tables"][0]
        cells = table["cells"]
        values = {(c["row_index"], c["column_index"]): c["value"] for c in cells}
        assert values[(0, 0)] == "Item"
        assert values[(1, 0)] == "Widget A"
        assert values[(3, 2)] == "500.00"

    def test_speaker_notes_as_footnote(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        slide3_blocks = result.pages[2]["text_blocks"]
        footnotes = [b for b in slide3_blocks if b["block_type"] == "footnote"]
        assert len(footnotes) == 1
        assert "speaker notes" in footnotes[0]["text"].lower()

    def test_metadata_extraction(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        assert result.metadata.get("title") == "Test Presentation"
        assert result.metadata.get("author") == "Test Author"
        assert result.metadata.get("slide_count") == 3

    def test_all_text_blocks_collected(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        assert len(result.text_blocks) > 0
        total_from_pages = sum(len(p["text_blocks"]) for p in result.pages)
        assert len(result.text_blocks) == total_from_pages

    def test_all_tables_collected(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        total_from_pages = sum(len(p["tables"]) for p in result.pages)
        assert len(result.tables) == total_from_pages


class TestPptxGraphBuilding:
    def test_graph_build_succeeds(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        builder = GraphBuilder()
        graph = builder.build(result, sample_pptx)
        assert graph.document.file_type == FileType.PPTX

    def test_graph_pages(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        builder = GraphBuilder()
        graph = builder.build(result, sample_pptx)
        assert len(graph.pages) == 3

    def test_graph_classified_as_presentation(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        builder = GraphBuilder()
        graph = builder.build(result, sample_pptx)
        assert DocumentType.PRESENTATION in graph.document.likely_document_types

    def test_graph_has_citations(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        builder = GraphBuilder()
        graph = builder.build(result, sample_pptx)
        assert len(graph.citations) > 0

    def test_graph_mime_type(self, adapter, sample_pptx):
        result = adapter.parse(sample_pptx, FileType.PPTX)
        builder = GraphBuilder()
        graph = builder.build(result, sample_pptx)
        assert "presentationml" in graph.document.mime_type


class TestPptxRegistry:
    def test_registry_detects_pptx(self):
        registry = ParserRegistry()
        ft = registry.detect_file_type(Path("test.pptx"))
        assert ft == FileType.PPTX

    def test_registry_finds_adapter(self):
        registry = ParserRegistry()
        adapter = registry.get_adapter(FileType.PPTX)
        assert adapter is not None
        assert isinstance(adapter, PptxAdapter)


class TestPptxEdgeCases:
    def test_nonexistent_file(self, adapter, tmp_path):
        result = adapter.parse(tmp_path / "nonexistent.pptx", FileType.PPTX)
        assert not result.success

    def test_empty_presentation(self, adapter, tmp_path):
        from pptx import Presentation

        prs = Presentation()
        path = tmp_path / "empty.pptx"
        prs.save(str(path))

        result = adapter.parse(path, FileType.PPTX)
        assert result.success
        assert result.page_count == 0
        assert any(w.code == "EMPTY_DOCUMENT" for w in result.warnings)
