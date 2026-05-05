"""Tests for XLS parser adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

from adx.models.document import FileType
from adx.parsers.xls_adapter import XlrdAdapter, _HAS_XLRD


@pytest.fixture
def adapter():
    return XlrdAdapter()


class TestXlrdAdapterCapabilities:
    def test_name(self, adapter):
        assert adapter.name() == "xlrd"

    def test_version_string(self, adapter):
        v = adapter.version()
        assert isinstance(v, str)

    @pytest.mark.skipif(not _HAS_XLRD, reason="xlrd not installed")
    def test_supports_xls_when_installed(self, adapter):
        assert adapter.supports(FileType.XLS)

    @pytest.mark.skipif(_HAS_XLRD, reason="xlrd is installed")
    def test_does_not_support_when_not_installed(self, adapter):
        assert not adapter.supports(FileType.XLS)

    def test_does_not_support_xlsx(self, adapter):
        assert not adapter.supports(FileType.XLSX)

    def test_does_not_support_pdf(self, adapter):
        assert not adapter.supports(FileType.PDF)


class TestXlrdFallback:
    @pytest.mark.skipif(_HAS_XLRD, reason="xlrd is installed")
    def test_fallback_error_when_not_installed(self, adapter, tmp_path):
        path = tmp_path / "test.xls"
        path.write_bytes(b"fake xls content")
        result = adapter.parse(path, FileType.XLS)
        assert not result.success
        assert any("xlrd" in e for e in result.errors)


@pytest.mark.skipif(not _HAS_XLRD, reason="xlrd not installed")
class TestXlrdParsing:
    @pytest.fixture
    def xls_path(self, tmp_path):
        import xlrd
        import xlwt

        wb = xlwt.Workbook()
        ws = wb.add_sheet("TestSheet")
        ws.write(0, 0, "Name")
        ws.write(0, 1, "Value")
        ws.write(1, 0, "Alpha")
        ws.write(1, 1, 100)
        ws.write(2, 0, "Beta")
        ws.write(2, 1, 200)
        path = tmp_path / "test.xls"
        wb.save(str(path))
        return path

    def test_parse_returns_result(self, adapter, xls_path):
        result = adapter.parse(xls_path, FileType.XLS)
        assert result.success

    def test_sheet_count(self, adapter, xls_path):
        result = adapter.parse(xls_path, FileType.XLS)
        assert result.sheet_count == 1

    def test_cells_extracted(self, adapter, xls_path):
        result = adapter.parse(xls_path, FileType.XLS)
        assert len(result.sheets) == 1
        cells = result.sheets[0]["cells"]
        assert len(cells) > 0

    def test_nonexistent_file(self, adapter, tmp_path):
        result = adapter.parse(tmp_path / "nope.xls", FileType.XLS)
        assert not result.success


class TestXlrdImport:
    def test_import_from_parsers(self):
        from adx.parsers import XlrdAdapter
        assert XlrdAdapter is not None
