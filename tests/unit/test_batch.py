"""Tests for batch directory upload."""

from __future__ import annotations

from pathlib import Path

import pytest

from adx.client import ADX
from adx.models.document import BatchResult


def _create_txt(path: Path, content: str = "hello") -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _create_csv(path: Path) -> Path:
    path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    return path


class TestBatchResultModel:
    def test_defaults(self):
        r = BatchResult()
        assert r.total_files == 0
        assert r.successful == 0
        assert r.failed == 0
        assert r.graphs == []
        assert r.errors == {}

    def test_serialization(self):
        r = BatchResult(total_files=3, successful=2, failed=1, graphs=["a", "b"], errors={"c": "err"})
        d = r.model_dump()
        assert d["total_files"] == 3
        assert d["errors"] == {"c": "err"}


class TestUploadDirectory:
    def test_empty_directory(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "empty"
        d.mkdir()
        result = client.upload_directory(d)
        assert result.total_files == 0
        assert result.successful == 0
        assert result.failed == 0

    def test_single_csv(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        d.mkdir()
        _create_csv(d / "test.csv")

        result = client.upload_directory(d)
        assert result.total_files == 1
        assert result.successful == 1
        assert result.failed == 0
        assert len(result.graphs) == 1

    def test_multiple_files(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        d.mkdir()
        _create_csv(d / "a.csv")
        _create_csv(d / "b.csv")

        result = client.upload_directory(d)
        assert result.total_files == 2
        assert result.successful == 2

    def test_recursive(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        sub = d / "sub"
        sub.mkdir(parents=True)
        _create_csv(d / "top.csv")
        _create_csv(sub / "nested.csv")

        result = client.upload_directory(d, recursive=True)
        assert result.total_files == 2
        assert result.successful == 2

    def test_non_recursive(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        sub = d / "sub"
        sub.mkdir(parents=True)
        _create_csv(d / "top.csv")
        _create_csv(sub / "nested.csv")

        result = client.upload_directory(d, recursive=False)
        assert result.total_files == 1
        assert result.successful == 1

    def test_unsupported_files_only(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        d.mkdir()
        (d / "file.xyz").write_text("unknown")

        result = client.upload_directory(d)
        assert result.total_files == 0

    def test_mixed_supported_and_unsupported(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        d.mkdir()
        _create_csv(d / "good.csv")
        (d / "file.xyz").write_text("unknown")

        result = client.upload_directory(d)
        assert result.total_files == 1
        assert result.successful == 1

    def test_extension_filter(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        d.mkdir()
        _create_csv(d / "a.csv")
        _create_txt(d / "b.txt")

        result = client.upload_directory(d, extensions={".csv"})
        assert result.total_files == 1
        assert result.successful == 1

    def test_partial_failures(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        d.mkdir()
        _create_csv(d / "good.csv")
        # Create a corrupt "PDF"
        (d / "bad.pdf").write_text("not a real pdf")

        result = client.upload_directory(d)
        assert result.total_files == 2
        assert result.successful == 1
        assert result.failed == 1
        assert len(result.errors) == 1

    def test_not_a_directory(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        f = tmp_path / "file.txt"
        f.write_text("hello")
        with pytest.raises(NotADirectoryError):
            client.upload_directory(f)

    def test_graphs_are_retrievable(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        d.mkdir()
        _create_csv(d / "test.csv")

        result = client.upload_directory(d)
        for fid in result.graphs:
            graph = client.get_graph(fid)
            assert graph is not None

    def test_batch_result_totals_consistent(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        d.mkdir()
        _create_csv(d / "a.csv")
        _create_csv(d / "b.csv")
        (d / "bad.pdf").write_text("corrupt")

        result = client.upload_directory(d)
        assert result.successful + result.failed == result.total_files
