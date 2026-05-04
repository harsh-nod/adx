"""Tests for DOCX and RTF parser adapters."""

from pathlib import Path

import pytest

from adx.models.document import FileType
from adx.parsers.docx_adapter import DocxAdapter
from adx.parsers.rtf_adapter import RTFAdapter
from adx.parsers.registry import ParserRegistry, EXTENSION_MAP
from adx.parsers.graph_builder import GraphBuilder

FIXTURES = Path(__file__).parent.parent / "fixtures"
DOCX_FIXTURE = FIXTURES / "docx" / "sample.docx"
RTF_FIXTURE = FIXTURES / "rtf" / "sample.rtf"


# ---------------------------------------------------------------------------
# FileType enum
# ---------------------------------------------------------------------------

class TestFileTypeExtensions:
    def test_rtf_in_filetype(self):
        assert FileType.RTF == "rtf"

    def test_docx_in_filetype(self):
        assert FileType.DOCX == "docx"

    def test_rtf_in_extension_map(self):
        assert ".rtf" in EXTENSION_MAP
        assert EXTENSION_MAP[".rtf"] == FileType.RTF

    def test_docx_in_extension_map(self):
        assert ".docx" in EXTENSION_MAP
        assert EXTENSION_MAP[".docx"] == FileType.DOCX


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_registry_has_docx_adapter(self):
        reg = ParserRegistry()
        adapter = reg.get_adapter(FileType.DOCX)
        assert adapter is not None
        assert isinstance(adapter, DocxAdapter)

    def test_registry_has_rtf_adapter(self):
        reg = ParserRegistry()
        adapter = reg.get_adapter(FileType.RTF)
        assert adapter is not None
        assert isinstance(adapter, RTFAdapter)

    def test_detect_docx(self):
        reg = ParserRegistry()
        assert reg.detect_file_type(Path("test.docx")) == FileType.DOCX

    def test_detect_rtf(self):
        reg = ParserRegistry()
        assert reg.detect_file_type(Path("test.rtf")) == FileType.RTF


# ---------------------------------------------------------------------------
# DOCX Adapter
# ---------------------------------------------------------------------------

class TestDocxAdapter:
    def test_name(self):
        assert DocxAdapter().name() == "python-docx"

    def test_capabilities(self):
        caps = DocxAdapter().capabilities()
        assert FileType.DOCX in caps.supported_types
        assert caps.extracts_text is True
        assert caps.extracts_tables is True
        assert caps.extracts_formulas is False

    def test_supports_docx(self):
        assert DocxAdapter().supports(FileType.DOCX) is True
        assert DocxAdapter().supports(FileType.PDF) is False

    def test_parse_sample(self):
        adapter = DocxAdapter()
        result = adapter.parse(DOCX_FIXTURE, FileType.DOCX)
        assert result.success
        assert result.page_count == 1
        assert len(result.text_blocks) > 0
        assert len(result.tables) > 0

    def test_heading_detection(self):
        adapter = DocxAdapter()
        result = adapter.parse(DOCX_FIXTURE, FileType.DOCX)
        headings = [b for b in result.text_blocks if b["block_type"] == "heading"]
        assert len(headings) >= 1
        # "Introduction" should be a heading
        heading_texts = [h["text"] for h in headings]
        assert "Introduction" in heading_texts

    def test_table_extraction(self):
        adapter = DocxAdapter()
        result = adapter.parse(DOCX_FIXTURE, FileType.DOCX)
        assert len(result.tables) == 1
        table = result.tables[0]
        assert table["row_count"] == 4
        assert table["column_count"] == 3
        # Check header row
        header_cells = [c for c in table["cells"] if c["row_index"] == 0]
        header_values = [c["value"] for c in header_cells]
        assert "Item" in header_values
        assert "Quantity" in header_values

    def test_metadata(self):
        adapter = DocxAdapter()
        result = adapter.parse(DOCX_FIXTURE, FileType.DOCX)
        assert "title" in result.metadata
        assert result.metadata["title"] == "Test Document"
        assert result.metadata["author"] == "Test Author"

    def test_parse_nonexistent(self):
        adapter = DocxAdapter()
        result = adapter.parse(Path("/nonexistent.docx"), FileType.DOCX)
        assert not result.success
        assert len(result.errors) > 0

    def test_parse_invalid_file(self, tmp_path):
        bad = tmp_path / "bad.docx"
        bad.write_text("this is not a docx file")
        adapter = DocxAdapter()
        result = adapter.parse(bad, FileType.DOCX)
        assert not result.success


# ---------------------------------------------------------------------------
# RTF Adapter
# ---------------------------------------------------------------------------

class TestRTFAdapter:
    def test_name(self):
        assert RTFAdapter().name() == "striprtf"

    def test_capabilities(self):
        caps = RTFAdapter().capabilities()
        assert FileType.RTF in caps.supported_types
        assert caps.extracts_text is True
        assert caps.extracts_tables is False

    def test_supports_rtf(self):
        assert RTFAdapter().supports(FileType.RTF) is True
        assert RTFAdapter().supports(FileType.PDF) is False

    def test_parse_sample(self):
        adapter = RTFAdapter()
        result = adapter.parse(RTF_FIXTURE, FileType.RTF)
        assert result.success
        assert result.page_count == 1
        assert len(result.text_blocks) > 0

    def test_text_content(self):
        adapter = RTFAdapter()
        result = adapter.parse(RTF_FIXTURE, FileType.RTF)
        all_text = " ".join(b["text"] for b in result.text_blocks)
        assert "Introduction" in all_text
        assert "test document" in all_text
        assert "500.00" in all_text

    def test_metadata(self):
        adapter = RTFAdapter()
        result = adapter.parse(RTF_FIXTURE, FileType.RTF)
        assert "paragraph_count" in result.metadata
        assert result.metadata["paragraph_count"] > 0

    def test_parse_nonexistent(self):
        adapter = RTFAdapter()
        result = adapter.parse(Path("/nonexistent.rtf"), FileType.RTF)
        assert not result.success

    def test_parse_empty(self, tmp_path):
        empty = tmp_path / "empty.rtf"
        empty.write_text(r"{\rtf1 }")
        adapter = RTFAdapter()
        result = adapter.parse(empty, FileType.RTF)
        assert result.success
        assert result.page_count == 1


# ---------------------------------------------------------------------------
# GraphBuilder integration
# ---------------------------------------------------------------------------

class TestGraphBuilderIntegration:
    def test_docx_graph(self):
        adapter = DocxAdapter()
        result = adapter.parse(DOCX_FIXTURE, FileType.DOCX)
        builder = GraphBuilder()
        graph = builder.build(result, DOCX_FIXTURE)
        assert graph.document.file_type == FileType.DOCX
        assert len(graph.pages) == 1
        assert len(graph.pages[0].text_blocks) > 0

    def test_rtf_graph(self):
        adapter = RTFAdapter()
        result = adapter.parse(RTF_FIXTURE, FileType.RTF)
        builder = GraphBuilder()
        graph = builder.build(result, RTF_FIXTURE)
        assert graph.document.file_type == FileType.RTF
        assert len(graph.pages) == 1
        assert len(graph.pages[0].text_blocks) > 0

    def test_docx_sections(self):
        adapter = DocxAdapter()
        result = adapter.parse(DOCX_FIXTURE, FileType.DOCX)
        builder = GraphBuilder()
        graph = builder.build(result, DOCX_FIXTURE)
        # Should detect sections from headings
        assert len(graph.sections) > 0
        section_titles = [s.title for s in graph.sections]
        assert "Introduction" in section_titles

    def test_docx_tables_in_graph(self):
        adapter = DocxAdapter()
        result = adapter.parse(DOCX_FIXTURE, FileType.DOCX)
        builder = GraphBuilder()
        graph = builder.build(result, DOCX_FIXTURE)
        all_tables = graph.get_all_tables()
        assert len(all_tables) > 0

    def test_docx_citations(self):
        adapter = DocxAdapter()
        result = adapter.parse(DOCX_FIXTURE, FileType.DOCX)
        builder = GraphBuilder()
        graph = builder.build(result, DOCX_FIXTURE)
        assert len(graph.citations) > 0
