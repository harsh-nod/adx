"""Tests for ParserRegistry.detect_file_type(), CSVAdapter.parse(), and adapter capabilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from docunav.models.document import FileType
from docunav.parsers.base import (
    ParserAdapter,
    ParserCapabilities,
    ParserResult,
    ParserWarning,
)
from docunav.parsers.csv_adapter import CSVAdapter, _col_letter
from docunav.parsers.registry import EXTENSION_MAP, ParserRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def csv_adapter():
    return CSVAdapter()


@pytest.fixture
def registry():
    return ParserRegistry()


@pytest.fixture
def simple_csv(tmp_path):
    """Create a small CSV file for testing."""
    content = "Name,Age,City\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago\n"
    path = tmp_path / "people.csv"
    path.write_text(content)
    return path


@pytest.fixture
def semicolon_csv(tmp_path):
    """CSV with semicolon delimiter."""
    content = "Name;Age;City\nAlice;30;NYC\nBob;25;LA\n"
    path = tmp_path / "semi.csv"
    path.write_text(content)
    return path


@pytest.fixture
def empty_csv(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    return path


@pytest.fixture
def single_column_csv(tmp_path):
    content = "Value\n100\n200\n300\n"
    path = tmp_path / "single.csv"
    path.write_text(content)
    return path


@pytest.fixture
def latin1_csv(tmp_path):
    content = "Name,City\nJos\xe9,S\xe3o Paulo\n"
    path = tmp_path / "latin1.csv"
    path.write_bytes(content.encode("latin-1"))
    return path


# ---------------------------------------------------------------------------
# ParserResult
# ---------------------------------------------------------------------------

class TestParserResult:
    def test_success_no_errors(self):
        result = ParserResult(
            parser_name="test",
            parser_version="1.0",
            file_type=FileType.CSV,
        )
        assert result.success is True

    def test_failure_with_errors(self):
        result = ParserResult(
            parser_name="test",
            parser_version="1.0",
            file_type=FileType.CSV,
            errors=["Something went wrong"],
        )
        assert result.success is False

    def test_default_fields(self):
        result = ParserResult(
            parser_name="test",
            parser_version="1.0",
            file_type=FileType.PDF,
        )
        assert result.pages == []
        assert result.tables == []
        assert result.sheets == []
        assert result.page_count == 0
        assert result.sheet_count == 0
        assert result.named_ranges == {}


class TestParserWarning:
    def test_creation(self):
        w = ParserWarning(code="TRUNCATED", message="File too large", page=5)
        assert w.code == "TRUNCATED"
        assert w.page == 5
        assert w.sheet is None


# ---------------------------------------------------------------------------
# CSVAdapter — capabilities
# ---------------------------------------------------------------------------

class TestCSVAdapterCapabilities:
    def test_name(self, csv_adapter):
        assert csv_adapter.name() == "csv_stdlib"

    def test_version(self, csv_adapter):
        assert csv_adapter.version() == "3.11"

    def test_capabilities(self, csv_adapter):
        caps = csv_adapter.capabilities()
        assert FileType.CSV in caps.supported_types
        assert caps.extracts_text is True
        assert caps.extracts_tables is True
        assert caps.extracts_layout is False
        assert caps.extracts_formulas is False
        assert caps.extracts_images is False
        assert caps.supports_ocr is False

    def test_supports_csv(self, csv_adapter):
        assert csv_adapter.supports(FileType.CSV) is True

    def test_does_not_support_pdf(self, csv_adapter):
        assert csv_adapter.supports(FileType.PDF) is False

    def test_does_not_support_xlsx(self, csv_adapter):
        assert csv_adapter.supports(FileType.XLSX) is False


# ---------------------------------------------------------------------------
# CSVAdapter — parse()
# ---------------------------------------------------------------------------

class TestCSVAdapterParse:
    def test_parse_simple_csv(self, csv_adapter, simple_csv):
        result = csv_adapter.parse(simple_csv, FileType.CSV)

        assert result.success is True
        assert result.parser_name == "csv_stdlib"
        assert result.file_type == FileType.CSV
        assert len(result.tables) == 1
        assert len(result.sheets) == 1
        assert result.sheet_count == 1

        table_data = result.tables[0]
        assert table_data["row_count"] == 4  # header + 3 data rows
        assert table_data["column_count"] == 3
        assert table_data["sheet_name"] == "Sheet1"
        assert table_data["title"] == "people"
        assert table_data["confidence"] == 1.0

        # Check cells
        cells = table_data["cells"]
        assert len(cells) == 12  # 4 rows * 3 columns
        # First cell should be "Name"
        first_cell = next(c for c in cells if c["row_index"] == 0 and c["column_index"] == 0)
        assert first_cell["value"] == "Name"

    def test_parse_semicolon_csv(self, csv_adapter, semicolon_csv):
        result = csv_adapter.parse(semicolon_csv, FileType.CSV)
        assert result.success is True
        table_data = result.tables[0]
        assert table_data["column_count"] == 3
        cells = table_data["cells"]
        first_cell = next(c for c in cells if c["row_index"] == 0 and c["column_index"] == 0)
        assert first_cell["value"] == "Name"

    def test_parse_empty_csv(self, csv_adapter, empty_csv):
        result = csv_adapter.parse(empty_csv, FileType.CSV)
        assert result.success is True  # no errors, just warnings
        assert len(result.tables) == 0
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "EMPTY_CSV"

    def test_parse_single_column(self, csv_adapter, single_column_csv):
        result = csv_adapter.parse(single_column_csv, FileType.CSV)
        assert result.success is True
        table_data = result.tables[0]
        assert table_data["column_count"] == 1
        assert table_data["row_count"] == 4

    def test_parse_latin1_encoding(self, csv_adapter, latin1_csv):
        result = csv_adapter.parse(latin1_csv, FileType.CSV)
        assert result.success is True
        cells = result.tables[0]["cells"]
        values = [c["value"] for c in cells]
        assert "Jos\xe9" in values

    def test_parse_nonexistent_file(self, csv_adapter, tmp_path):
        path = tmp_path / "nonexistent.csv"
        result = csv_adapter.parse(path, FileType.CSV)
        assert result.success is False
        assert len(result.errors) == 1
        assert "Failed to read CSV" in result.errors[0]

    def test_sheet_metadata(self, csv_adapter, simple_csv):
        result = csv_adapter.parse(simple_csv, FileType.CSV)
        sheet = result.sheets[0]
        assert sheet["name"] == "Sheet1"
        assert sheet["index"] == 0
        assert sheet["is_visible"] is True
        assert sheet["row_count"] == 4
        assert sheet["column_count"] == 3
        assert sheet["used_range"].startswith("A1:")

    def test_metadata_in_result(self, csv_adapter, simple_csv):
        result = csv_adapter.parse(simple_csv, FileType.CSV)
        assert result.metadata["row_count"] == 4
        assert result.metadata["column_count"] == 3
        assert result.metadata["truncated"] is False


# ---------------------------------------------------------------------------
# _col_letter helper
# ---------------------------------------------------------------------------

class TestColLetter:
    def test_single_letter_columns(self):
        assert _col_letter(1) == "A"
        assert _col_letter(26) == "Z"

    def test_double_letter_columns(self):
        assert _col_letter(27) == "AA"
        assert _col_letter(28) == "AB"
        assert _col_letter(52) == "AZ"

    def test_zero_returns_A(self):
        assert _col_letter(0) == "A"


# ---------------------------------------------------------------------------
# ParserRegistry — detect_file_type()
# ---------------------------------------------------------------------------

class TestParserRegistryDetectFileType:
    def test_pdf(self, registry):
        assert registry.detect_file_type(Path("test.pdf")) == FileType.PDF

    def test_xlsx(self, registry):
        assert registry.detect_file_type(Path("test.xlsx")) == FileType.XLSX

    def test_xls(self, registry):
        assert registry.detect_file_type(Path("test.xls")) == FileType.XLS

    def test_csv(self, registry):
        assert registry.detect_file_type(Path("test.csv")) == FileType.CSV

    def test_docx(self, registry):
        assert registry.detect_file_type(Path("test.docx")) == FileType.DOCX

    def test_txt(self, registry):
        assert registry.detect_file_type(Path("test.txt")) == FileType.TEXT

    def test_png(self, registry):
        assert registry.detect_file_type(Path("test.png")) == FileType.IMAGE

    def test_jpg(self, registry):
        assert registry.detect_file_type(Path("test.jpg")) == FileType.IMAGE

    def test_jpeg(self, registry):
        assert registry.detect_file_type(Path("test.jpeg")) == FileType.IMAGE

    def test_tiff(self, registry):
        assert registry.detect_file_type(Path("test.tiff")) == FileType.IMAGE

    def test_unknown_extension(self, registry):
        assert registry.detect_file_type(Path("test.xyz")) == FileType.UNKNOWN

    def test_case_insensitive(self, registry):
        assert registry.detect_file_type(Path("test.PDF")) == FileType.PDF
        assert registry.detect_file_type(Path("test.Csv")) == FileType.CSV

    def test_no_extension(self, registry):
        assert registry.detect_file_type(Path("Makefile")) == FileType.UNKNOWN


# ---------------------------------------------------------------------------
# ParserRegistry — get_adapter and register
# ---------------------------------------------------------------------------

class TestParserRegistryAdapters:
    def test_get_adapter_csv(self, registry):
        adapter = registry.get_adapter(FileType.CSV)
        assert adapter is not None
        assert isinstance(adapter, CSVAdapter)

    def test_get_adapter_unknown(self, registry):
        adapter = registry.get_adapter(FileType.UNKNOWN)
        assert adapter is None

    def test_register_custom_adapter(self, registry):
        class DummyAdapter(ParserAdapter):
            def name(self):
                return "dummy"

            def version(self):
                return "0.1"

            def capabilities(self):
                return ParserCapabilities(supported_types=[FileType.TEXT])

            def parse(self, file_path, file_type):
                return ParserResult(
                    parser_name=self.name(),
                    parser_version=self.version(),
                    file_type=file_type,
                )

        registry.register(DummyAdapter())
        adapter = registry.get_adapter(FileType.TEXT)
        assert adapter is not None
        assert adapter.name() == "dummy"

    def test_parse_unsupported_returns_error(self, registry):
        result = registry.parse(Path("file.xyz"), FileType.UNKNOWN)
        assert result.success is False
        assert "No parser available" in result.errors[0]

    def test_parse_csv_via_registry(self, registry, simple_csv):
        result = registry.parse(simple_csv)
        assert result.success is True
        assert result.parser_name == "csv_stdlib"

    def test_parse_csv_with_explicit_type(self, registry, simple_csv):
        result = registry.parse(simple_csv, FileType.CSV)
        assert result.success is True


# ---------------------------------------------------------------------------
# EXTENSION_MAP coverage
# ---------------------------------------------------------------------------

class TestExtensionMap:
    def test_all_known_extensions(self):
        expected = {
            ".pdf", ".xlsx", ".xls", ".csv", ".docx", ".txt",
            ".png", ".jpg", ".jpeg", ".tiff", ".tif",
        }
        assert set(EXTENSION_MAP.keys()) == expected
