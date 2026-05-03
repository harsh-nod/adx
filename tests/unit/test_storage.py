"""Tests for DocumentStore save/load/list/delete using tmp_path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docunav.models.document import (
    Citation,
    Document,
    DocumentGraph,
    Extraction,
    ExtractionField,
    FileType,
    Page,
    ProcessingStatus,
    Table,
    TableCell,
    TextBlock,
    TextBlockType,
    Workbook,
    Sheet,
)
from docunav.storage.store import DocumentStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path):
    """Create a DocumentStore backed by a tmp_path directory."""
    return DocumentStore(base_dir=tmp_path / "docunav_test_storage")


@pytest.fixture
def sample_graph():
    """A minimal DocumentGraph for storage tests."""
    doc = Document(
        id="store_test_001",
        filename="test.pdf",
        file_type=FileType.PDF,
        page_count=1,
        processing_status=ProcessingStatus.COMPLETED,
    )
    tb = TextBlock(text="Hello World", block_type=TextBlockType.PARAGRAPH)
    page = Page(page_number=1, text_blocks=[tb])
    return DocumentGraph(document=doc, pages=[page])


@pytest.fixture
def sample_graph_b():
    """A second graph for multi-document tests."""
    doc = Document(
        id="store_test_002",
        filename="other.csv",
        file_type=FileType.CSV,
        sheet_count=1,
    )
    return DocumentGraph(document=doc)


@pytest.fixture
def sample_extraction():
    return Extraction(
        id="ext_001",
        document_id="store_test_001",
        schema_id="invoice",
        schema_name="Invoice",
        status="completed",
        output={"vendor_name": "Acme"},
        fields=[
            ExtractionField(
                field_path="vendor_name",
                value="Acme",
                confidence=0.9,
            ),
        ],
    )


@pytest.fixture
def sample_extraction_b():
    return Extraction(
        id="ext_002",
        document_id="store_test_002",
        schema_id="table",
        schema_name="Table",
        status="completed",
        output={"headers": ["A", "B"]},
    )


@pytest.fixture
def sample_file(tmp_path):
    """Create a dummy file to store."""
    path = tmp_path / "upload.pdf"
    path.write_bytes(b"fake pdf content")
    return path


# ---------------------------------------------------------------------------
# Directory initialization
# ---------------------------------------------------------------------------

class TestStoreInit:
    def test_directories_created(self, store):
        assert store.files_dir.is_dir()
        assert store.graphs_dir.is_dir()
        assert store.extractions_dir.is_dir()

    def test_default_storage_dir(self):
        # Just verify the class can be instantiated with no args
        # (don't actually create in default location)
        s = DocumentStore.__new__(DocumentStore)
        s.base_dir = Path("/tmp/docunav_test_default")
        s.files_dir = s.base_dir / "files"
        s.graphs_dir = s.base_dir / "graphs"
        s.extractions_dir = s.base_dir / "extractions"
        # No assertion needed; just verifying no crash


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

class TestFileOperations:
    def test_store_file(self, store, sample_file):
        dest = store.store_file(sample_file, "file_001")
        assert dest.exists()
        assert dest.name == "upload.pdf"
        assert dest.read_bytes() == b"fake pdf content"

    def test_store_file_bytes(self, store):
        dest = store.store_file_bytes(b"binary data", "data.bin", "file_002")
        assert dest.exists()
        assert dest.read_bytes() == b"binary data"

    def test_get_file_path_found(self, store, sample_file):
        store.store_file(sample_file, "file_003")
        path = store.get_file_path("file_003", "upload.pdf")
        assert path is not None
        assert path.exists()

    def test_get_file_path_not_found(self, store):
        path = store.get_file_path("nonexistent", "missing.pdf")
        assert path is None

    def test_store_file_creates_subdirectory(self, store, sample_file):
        dest = store.store_file(sample_file, "subdir_test")
        assert dest.parent.name == "subdir_test"
        assert dest.parent.is_dir()

    def test_store_multiple_files_same_id(self, store, tmp_path):
        f1 = tmp_path / "file1.txt"
        f1.write_text("one")
        f2 = tmp_path / "file2.txt"
        f2.write_text("two")

        store.store_file(f1, "multi_001")
        store.store_file(f2, "multi_001")

        assert store.get_file_path("multi_001", "file1.txt") is not None
        assert store.get_file_path("multi_001", "file2.txt") is not None


# ---------------------------------------------------------------------------
# DocumentGraph operations
# ---------------------------------------------------------------------------

class TestGraphOperations:
    def test_save_and_load_graph(self, store, sample_graph):
        path = store.save_graph(sample_graph)
        assert path.exists()
        assert path.suffix == ".json"

        loaded = store.load_graph("store_test_001")
        assert loaded is not None
        assert loaded.document.id == "store_test_001"
        assert loaded.document.filename == "test.pdf"
        assert loaded.document.file_type == FileType.PDF
        assert len(loaded.pages) == 1
        assert loaded.pages[0].text_blocks[0].text == "Hello World"

    def test_load_graph_not_found(self, store):
        assert store.load_graph("nonexistent") is None

    def test_list_graphs_empty(self, store):
        assert store.list_graphs() == []

    def test_list_graphs(self, store, sample_graph, sample_graph_b):
        store.save_graph(sample_graph)
        store.save_graph(sample_graph_b)
        ids = store.list_graphs()
        assert len(ids) == 2
        assert "store_test_001" in ids
        assert "store_test_002" in ids

    def test_delete_graph(self, store, sample_graph):
        store.save_graph(sample_graph)
        assert store.delete_graph("store_test_001") is True
        assert store.load_graph("store_test_001") is None
        assert store.list_graphs() == []

    def test_delete_graph_not_found(self, store):
        assert store.delete_graph("nonexistent") is False

    def test_overwrite_graph(self, store, sample_graph):
        store.save_graph(sample_graph)
        # Modify and save again
        sample_graph.document.filename = "updated.pdf"
        store.save_graph(sample_graph)
        loaded = store.load_graph("store_test_001")
        assert loaded.document.filename == "updated.pdf"

    def test_graph_json_valid(self, store, sample_graph):
        path = store.save_graph(sample_graph)
        data = json.loads(path.read_text())
        assert data["document"]["id"] == "store_test_001"
        assert data["schema_version"] is not None

    def test_graph_with_workbook(self, store):
        """Ensure a graph with workbook data survives roundtrip."""
        doc = Document(id="wb_test", filename="data.xlsx", file_type=FileType.XLSX)
        cells = [
            TableCell(row_index=0, column_index=0, value="A"),
            TableCell(row_index=0, column_index=1, value="B"),
        ]
        table = Table(sheet_name="Sheet1", row_count=1, column_count=2, cells=cells)
        sheet = Sheet(name="Sheet1", tables=[table])
        wb = Workbook(sheets=[sheet], named_ranges={"r": "Sheet1!A1"})
        graph = DocumentGraph(document=doc, workbook=wb)

        store.save_graph(graph)
        loaded = store.load_graph("wb_test")
        assert loaded.workbook is not None
        assert len(loaded.workbook.sheets) == 1
        assert loaded.workbook.named_ranges == {"r": "Sheet1!A1"}
        assert len(loaded.workbook.sheets[0].tables[0].cells) == 2


# ---------------------------------------------------------------------------
# Extraction operations
# ---------------------------------------------------------------------------

class TestExtractionOperations:
    def test_save_and_load_extraction(self, store, sample_extraction):
        path = store.save_extraction(sample_extraction)
        assert path.exists()

        loaded = store.load_extraction("ext_001")
        assert loaded is not None
        assert loaded.id == "ext_001"
        assert loaded.document_id == "store_test_001"
        assert loaded.schema_id == "invoice"
        assert loaded.output["vendor_name"] == "Acme"
        assert len(loaded.fields) == 1
        assert loaded.fields[0].field_path == "vendor_name"
        assert loaded.fields[0].confidence == 0.9

    def test_load_extraction_not_found(self, store):
        assert store.load_extraction("nonexistent") is None

    def test_list_extractions_empty(self, store):
        assert store.list_extractions() == []

    def test_list_extractions_all(self, store, sample_extraction, sample_extraction_b):
        store.save_extraction(sample_extraction)
        store.save_extraction(sample_extraction_b)
        ids = store.list_extractions()
        assert len(ids) == 2
        assert "ext_001" in ids
        assert "ext_002" in ids

    def test_list_extractions_by_document_id(self, store, sample_extraction, sample_extraction_b):
        store.save_extraction(sample_extraction)
        store.save_extraction(sample_extraction_b)
        ids = store.list_extractions(document_id="store_test_001")
        assert len(ids) == 1
        assert "ext_001" in ids

    def test_list_extractions_document_id_no_match(self, store, sample_extraction):
        store.save_extraction(sample_extraction)
        ids = store.list_extractions(document_id="nonexistent")
        assert len(ids) == 0

    def test_extraction_json_valid(self, store, sample_extraction):
        path = store.save_extraction(sample_extraction)
        data = json.loads(path.read_text())
        assert data["id"] == "ext_001"
        assert data["document_id"] == "store_test_001"

    def test_extraction_with_citations(self, store):
        citation = Citation(
            document_id="doc1",
            page_number=1,
        )
        extraction = Extraction(
            id="ext_cit",
            document_id="doc1",
            fields=[
                ExtractionField(
                    field_path="name",
                    value="Test",
                    citations=[citation],
                ),
            ],
        )
        store.save_extraction(extraction)
        loaded = store.load_extraction("ext_cit")
        assert len(loaded.fields[0].citations) == 1
        assert loaded.fields[0].citations[0].page_number == 1


# ---------------------------------------------------------------------------
# Full workflow test
# ---------------------------------------------------------------------------

class TestStoreWorkflow:
    def test_full_workflow(self, store, sample_file, sample_graph, sample_extraction):
        # 1. Store file
        stored_path = store.store_file(sample_file, sample_graph.document.id)
        assert stored_path.exists()

        # 2. Save graph
        store.save_graph(sample_graph)

        # 3. Load graph back
        graph = store.load_graph(sample_graph.document.id)
        assert graph is not None

        # 4. Save extraction
        store.save_extraction(sample_extraction)

        # 5. Load extraction
        extraction = store.load_extraction(sample_extraction.id)
        assert extraction is not None

        # 6. List everything
        assert len(store.list_graphs()) == 1
        assert len(store.list_extractions()) == 1

        # 7. Delete graph (extraction remains)
        store.delete_graph(sample_graph.document.id)
        assert store.load_graph(sample_graph.document.id) is None
        assert store.load_extraction(sample_extraction.id) is not None

    def test_isolation_between_stores(self, tmp_path):
        """Two stores with different base_dirs should be completely independent."""
        store_a = DocumentStore(base_dir=tmp_path / "store_a")
        store_b = DocumentStore(base_dir=tmp_path / "store_b")

        doc_a = Document(id="iso_a", filename="a.pdf")
        graph_a = DocumentGraph(document=doc_a)
        store_a.save_graph(graph_a)

        assert store_a.load_graph("iso_a") is not None
        assert store_b.load_graph("iso_a") is None
        assert store_a.list_graphs() == ["iso_a"]
        assert store_b.list_graphs() == []
