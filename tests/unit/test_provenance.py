"""Tests for byte-range provenance on citations."""

from __future__ import annotations

from pathlib import Path

import pytest

from adx.models.document import Citation, CitationType


class TestCitationByteRange:
    def test_citation_with_byte_range(self):
        c = Citation(
            document_id="doc1",
            citation_type=CitationType.PAGE,
            page_number=1,
            source_byte_start=0,
            source_byte_end=100,
        )
        assert c.source_byte_start == 0
        assert c.source_byte_end == 100

    def test_citation_without_byte_range(self):
        c = Citation(document_id="doc1", citation_type=CitationType.PAGE, page_number=1)
        assert c.source_byte_start is None
        assert c.source_byte_end is None

    def test_short_ref_with_byte_range(self):
        c = Citation(
            document_id="doc1",
            citation_type=CitationType.PAGE,
            page_number=1,
            source_byte_start=100,
            source_byte_end=200,
        )
        ref = c.to_short_ref()
        assert "bytes 100-200" in ref
        assert "page 1" in ref

    def test_short_ref_without_byte_range(self):
        c = Citation(
            document_id="doc1",
            citation_type=CitationType.PAGE,
            page_number=1,
        )
        ref = c.to_short_ref()
        assert "bytes" not in ref

    def test_serialization_includes_byte_range(self):
        c = Citation(
            document_id="doc1",
            citation_type=CitationType.PAGE,
            source_byte_start=50,
            source_byte_end=150,
        )
        d = c.model_dump()
        assert d["source_byte_start"] == 50
        assert d["source_byte_end"] == 150

    def test_serialization_null_byte_range(self):
        c = Citation(document_id="doc1", citation_type=CitationType.PAGE)
        d = c.model_dump()
        assert d["source_byte_start"] is None
        assert d["source_byte_end"] is None


class TestPdfAdapterByteOffsets:
    """Test that the PDF adapter emits byte offsets in text block data."""

    @pytest.fixture
    def pdf_fixture(self):
        pdf_path = Path(__file__).parent.parent / "fixtures" / "pdfs" / "sample.pdf"
        if not pdf_path.exists():
            pytest.skip("PDF fixture not available")
        return pdf_path

    def test_pdf_text_blocks_have_byte_offsets(self, pdf_fixture):
        from adx.parsers.pdf_adapter import PyMuPDFAdapter
        from adx.models.document import FileType

        adapter = PyMuPDFAdapter()
        result = adapter.parse(pdf_fixture, FileType.PDF)
        assert result.success

        for page_data in result.pages:
            for tb in page_data.get("text_blocks", []):
                assert "byte_offset_start" in tb
                assert "byte_offset_end" in tb
                assert tb["byte_offset_start"] >= 0
                assert tb["byte_offset_end"] > tb["byte_offset_start"]

    def test_byte_offsets_monotonically_increase(self, pdf_fixture):
        from adx.parsers.pdf_adapter import PyMuPDFAdapter
        from adx.models.document import FileType

        adapter = PyMuPDFAdapter()
        result = adapter.parse(pdf_fixture, FileType.PDF)

        all_offsets = []
        for page_data in result.pages:
            for tb in page_data.get("text_blocks", []):
                all_offsets.append((tb["byte_offset_start"], tb["byte_offset_end"]))

        for i in range(1, len(all_offsets)):
            assert all_offsets[i][0] >= all_offsets[i - 1][0]


class TestGraphBuilderPropagation:
    """Test that graph builder propagates byte offsets to citations."""

    @pytest.fixture
    def pdf_fixture(self):
        pdf_path = Path(__file__).parent.parent / "fixtures" / "pdfs" / "sample.pdf"
        if not pdf_path.exists():
            pytest.skip("PDF fixture not available")
        return pdf_path

    def test_citations_have_byte_ranges(self, pdf_fixture):
        from adx.parsers.pdf_adapter import PyMuPDFAdapter
        from adx.parsers.graph_builder import GraphBuilder
        from adx.models.document import FileType

        adapter = PyMuPDFAdapter()
        result = adapter.parse(pdf_fixture, FileType.PDF)
        builder = GraphBuilder()
        graph = builder.build(result, pdf_fixture)

        text_citations = [
            c for c in graph.citations
            if c.citation_type in (CitationType.PAGE, CitationType.BOUNDING_BOX)
            and c.source_byte_start is not None
        ]
        assert len(text_citations) > 0

    def test_byte_ranges_positive(self, pdf_fixture):
        from adx.parsers.pdf_adapter import PyMuPDFAdapter
        from adx.parsers.graph_builder import GraphBuilder
        from adx.models.document import FileType

        adapter = PyMuPDFAdapter()
        result = adapter.parse(pdf_fixture, FileType.PDF)
        builder = GraphBuilder()
        graph = builder.build(result, pdf_fixture)

        for c in graph.citations:
            if c.source_byte_start is not None:
                assert c.source_byte_start >= 0
                assert c.source_byte_end > c.source_byte_start


class TestChunkingPreservesProvenance:
    """Test that chunking preserves citation byte ranges."""

    @pytest.fixture
    def pdf_fixture(self):
        pdf_path = Path(__file__).parent.parent / "fixtures" / "pdfs" / "sample.pdf"
        if not pdf_path.exists():
            pytest.skip("PDF fixture not available")
        return pdf_path

    def test_chunk_citations_have_provenance(self, pdf_fixture):
        from adx.parsers.pdf_adapter import PyMuPDFAdapter
        from adx.parsers.graph_builder import GraphBuilder
        from adx.chunking import ChunkingConfig, chunk_document
        from adx.models.document import FileType

        adapter = PyMuPDFAdapter()
        result = adapter.parse(pdf_fixture, FileType.PDF)
        builder = GraphBuilder()
        graph = builder.build(result, pdf_fixture)

        chunks = chunk_document(graph, ChunkingConfig(include_tables=False))
        assert len(chunks) > 0

        # Each text chunk should have citations
        text_chunks = [c for c in chunks if c.chunk_type == "text"]
        for chunk in text_chunks:
            assert len(chunk.citations) > 0
