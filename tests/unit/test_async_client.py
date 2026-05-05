"""Tests for the async ADX client."""

from __future__ import annotations

from pathlib import Path

import pytest

from adx.async_client import AsyncADX


@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "test.csv"
    p.write_text("name,value\nfoo,1\nbar,2\n")
    return p


@pytest.fixture
def async_client(tmp_path):
    return AsyncADX(storage_dir=tmp_path / "store")


class TestAsyncUpload:
    async def test_upload(self, async_client, csv_path):
        graph = await async_client.upload(csv_path)
        assert graph.document.filename == "test.csv"

    async def test_upload_bytes(self, async_client):
        data = b"a,b\n1,2\n"
        graph = await async_client.upload_bytes(data, "data.csv")
        assert graph.document.filename == "data.csv"

    async def test_list_files(self, async_client, csv_path):
        await async_client.upload(csv_path)
        files = await async_client.list_files()
        assert len(files) == 1


class TestAsyncGetGraph:
    async def test_get_graph(self, async_client, csv_path):
        graph = await async_client.upload(csv_path)
        loaded = await async_client.get_graph(graph.document.id)
        assert loaded is not None
        assert loaded.document.id == graph.document.id

    async def test_get_graph_not_found(self, async_client):
        result = await async_client.get_graph("nonexistent")
        assert result is None


class TestAsyncMarkdown:
    async def test_to_markdown(self, async_client, csv_path):
        graph = await async_client.upload(csv_path)
        md = await async_client.to_markdown(graph.document.id)
        assert isinstance(md, str)
        assert len(md) > 0


class TestAsyncBatch:
    async def test_upload_directory(self, async_client, tmp_path):
        d = tmp_path / "data"
        d.mkdir()
        (d / "a.csv").write_text("x,y\n1,2\n")
        (d / "b.csv").write_text("x,y\n3,4\n")

        result = await async_client.upload_directory(d)
        assert result.successful == 2

    async def test_upload_many(self, async_client, tmp_path):
        paths = []
        for name in ["a.csv", "b.csv", "c.csv"]:
            p = tmp_path / name
            p.write_text(f"col\n{name}\n")
            paths.append(p)

        graphs = await async_client.upload_many(paths)
        assert len(graphs) == 3


class TestAsyncSearch:
    async def test_search_corpus(self, async_client, csv_path):
        await async_client.upload(csv_path)
        hits = await async_client.search_corpus("foo")
        assert isinstance(hits, list)
        assert len(hits) > 0

    async def test_search(self, async_client, csv_path):
        graph = await async_client.upload(csv_path)
        result = await async_client.search(graph.document.id, "foo")
        assert isinstance(result, dict)


class TestAsyncChunk:
    async def test_chunk(self, async_client, csv_path):
        graph = await async_client.upload(csv_path)
        chunks = await async_client.chunk(graph.document.id)
        assert len(chunks) > 0


class TestAsyncExtract:
    async def test_extract(self, async_client, csv_path):
        graph = await async_client.upload(csv_path)
        extraction = await async_client.extract(graph.document.id)
        assert extraction.id is not None


class TestAsyncImport:
    def test_import_from_package(self):
        from adx import AsyncADX as Imported
        assert Imported is AsyncADX
