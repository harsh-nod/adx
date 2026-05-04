"""Tests for the chunking API."""

from __future__ import annotations

from pathlib import Path

import pytest

from adx.chunking import Chunk, ChunkingConfig, chunk_document
from adx.chunking.strategies import fixed_size_chunks, section_aware_chunks, table_as_chunk
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


def _graph_with_text(texts, headings=None, sections=None, tables=None):
    blocks = []
    for i, text in enumerate(texts):
        bt = TextBlockType.PARAGRAPH
        if headings and i in headings:
            bt = TextBlockType.HEADING
        blocks.append(TextBlock(
            text=text, block_type=bt, reading_order_index=i, page_number=1,
        ))
    page = Page(page_number=1, text_blocks=blocks, tables=tables or [])
    return DocumentGraph(
        document=Document(filename="test.pdf", file_type=FileType.PDF),
        pages=[page],
        sections=sections or [],
    )


class TestChunkingConfig:
    def test_defaults(self):
        cfg = ChunkingConfig()
        assert cfg.strategy == "section_aware"
        assert cfg.max_chunk_size == 1000
        assert cfg.overlap == 200
        assert cfg.include_tables is True

    def test_custom_config(self):
        cfg = ChunkingConfig(strategy="fixed_size", max_chunk_size=500, overlap=100)
        assert cfg.strategy == "fixed_size"
        assert cfg.max_chunk_size == 500


class TestChunkModel:
    def test_defaults(self):
        c = Chunk()
        assert c.text == ""
        assert c.chunk_type == "text"
        assert c.citations == []
        assert c.section_path == []
        assert c.page_numbers == []
        assert c.token_count == 0

    def test_id_generated(self):
        c = Chunk()
        assert c.id.startswith("chunk-")


class TestFixedSizeChunking:
    def test_single_short_text(self):
        graph = _graph_with_text(["Hello world"])
        chunks = fixed_size_chunks(graph, ChunkingConfig(strategy="fixed_size"))
        assert len(chunks) >= 1
        assert "Hello world" in chunks[0].text

    def test_splits_long_text(self):
        long_text = "word " * 2000
        graph = _graph_with_text([long_text])
        cfg = ChunkingConfig(strategy="fixed_size", max_chunk_size=100)
        chunks = fixed_size_chunks(graph, cfg)
        assert len(chunks) > 1

    def test_overlap(self):
        long_text = "word " * 2000
        graph = _graph_with_text([long_text])
        cfg_with = ChunkingConfig(strategy="fixed_size", max_chunk_size=100, overlap=50)
        cfg_without = ChunkingConfig(strategy="fixed_size", max_chunk_size=100, overlap=0)
        chunks_with = fixed_size_chunks(graph, cfg_with)
        chunks_without = fixed_size_chunks(graph, cfg_without)
        # More chunks with overlap
        assert len(chunks_with) >= len(chunks_without)

    def test_empty_document(self):
        graph = _graph_with_text([])
        chunks = fixed_size_chunks(graph, ChunkingConfig())
        assert chunks == []

    def test_token_count_set(self):
        graph = _graph_with_text(["Hello world this is a test"])
        chunks = fixed_size_chunks(graph, ChunkingConfig())
        assert chunks[0].token_count > 0


class TestSectionAwareChunking:
    def test_splits_at_headings(self):
        graph = _graph_with_text(
            ["Heading 1", "Body 1", "Heading 2", "Body 2"],
            headings={0, 2},
            sections=[
                Section(title="Heading 1", heading_level=1),
                Section(title="Heading 2", heading_level=1),
            ],
        )
        chunks = section_aware_chunks(graph, ChunkingConfig(include_tables=False))
        text_chunks = [c for c in chunks if c.chunk_type == "text"]
        assert len(text_chunks) >= 2

    def test_section_path_populated(self):
        graph = _graph_with_text(
            ["Main", "Content"],
            headings={0},
            sections=[Section(title="Main", heading_level=1)],
        )
        chunks = section_aware_chunks(graph, ChunkingConfig(include_tables=False))
        text_chunks = [c for c in chunks if c.chunk_type == "text"]
        assert any("Main" in c.section_path for c in text_chunks)

    def test_includes_tables_by_default(self):
        table = Table(
            row_count=2, column_count=2,
            cells=[
                TableCell(row_index=0, column_index=0, value="A"),
                TableCell(row_index=0, column_index=1, value="B"),
                TableCell(row_index=1, column_index=0, value="1"),
                TableCell(row_index=1, column_index=1, value="2"),
            ],
        )
        graph = _graph_with_text(["Text"], tables=[table])
        chunks = section_aware_chunks(graph, ChunkingConfig())
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        assert len(table_chunks) >= 1

    def test_citations_populated(self):
        graph = _graph_with_text(["Hello world paragraph"])
        chunks = section_aware_chunks(graph, ChunkingConfig(include_tables=False))
        text_chunks = [c for c in chunks if c.chunk_type == "text"]
        assert len(text_chunks) > 0
        assert len(text_chunks[0].citations) > 0

    def test_page_numbers_tracked(self):
        graph = _graph_with_text(["Content"])
        chunks = section_aware_chunks(graph, ChunkingConfig(include_tables=False))
        text_chunks = [c for c in chunks if c.chunk_type == "text"]
        assert 1 in text_chunks[0].page_numbers

    def test_skips_header_footer(self):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text="Header", block_type=TextBlockType.HEADER, reading_order_index=0),
                TextBlock(text="Body", block_type=TextBlockType.PARAGRAPH, reading_order_index=1),
                TextBlock(text="Footer", block_type=TextBlockType.FOOTER, reading_order_index=2),
            ],
        )
        graph = DocumentGraph(
            document=Document(filename="test.pdf", file_type=FileType.PDF),
            pages=[page],
        )
        chunks = section_aware_chunks(graph, ChunkingConfig(include_tables=False))
        all_text = " ".join(c.text for c in chunks)
        assert "Header" not in all_text
        assert "Footer" not in all_text
        assert "Body" in all_text


class TestTableAsChunk:
    def test_page_table_as_chunk(self):
        table = Table(
            row_count=2, column_count=1,
            cells=[
                TableCell(row_index=0, column_index=0, value="H"),
                TableCell(row_index=1, column_index=0, value="V"),
            ],
        )
        page = Page(page_number=1, tables=[table])
        graph = DocumentGraph(
            document=Document(filename="test.pdf", file_type=FileType.PDF),
            pages=[page],
        )
        chunks = table_as_chunk(graph, ChunkingConfig())
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "table"
        assert "| H |" in chunks[0].text

    def test_workbook_table_as_chunk(self):
        table = Table(
            sheet_name="Sheet1", row_count=1, column_count=1,
            cells=[TableCell(row_index=0, column_index=0, value="X")],
        )
        sheet = Sheet(name="Sheet1", tables=[table])
        wb = Workbook(sheets=[sheet])
        graph = DocumentGraph(
            document=Document(filename="test.xlsx", file_type=FileType.XLSX),
            workbook=wb,
        )
        chunks = table_as_chunk(graph, ChunkingConfig())
        assert len(chunks) == 1
        assert chunks[0].sheet_name == "Sheet1"


class TestChunkDocumentDispatcher:
    def test_default_strategy(self):
        graph = _graph_with_text(["Content"])
        chunks = chunk_document(graph)
        assert len(chunks) > 0

    def test_fixed_size_strategy(self):
        graph = _graph_with_text(["Content"])
        cfg = ChunkingConfig(strategy="fixed_size")
        chunks = chunk_document(graph, cfg)
        assert len(chunks) > 0

    def test_table_only_strategy(self):
        table = Table(
            row_count=1, column_count=1,
            cells=[TableCell(row_index=0, column_index=0, value="X")],
        )
        graph = _graph_with_text(["Text"], tables=[table])
        cfg = ChunkingConfig(strategy="table_only")
        chunks = chunk_document(graph, cfg)
        assert all(c.chunk_type == "table" for c in chunks)

    def test_unknown_strategy_raises(self):
        graph = _graph_with_text(["Content"])
        cfg = ChunkingConfig(strategy="nonexistent")
        with pytest.raises(ValueError, match="Unknown chunking strategy"):
            chunk_document(graph, cfg)

    def test_empty_document(self):
        graph = _graph_with_text([])
        chunks = chunk_document(graph, ChunkingConfig(include_tables=False))
        assert chunks == []


class TestChunkClientIntegration:
    def test_client_chunk(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("a,b\n1,2\n3,4\n")

        client = ADX(storage_dir=tmp_path / "store")
        graph = client.upload(csv_path)
        chunks = client.chunk(graph.document.id)
        assert len(chunks) > 0

    def test_client_chunk_not_found(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        with pytest.raises(ValueError, match="not found"):
            client.chunk("nonexistent")
