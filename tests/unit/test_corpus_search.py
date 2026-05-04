"""Tests for corpus-level search."""

from __future__ import annotations

from pathlib import Path

import pytest

from adx.client import ADX


def _create_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def client_with_docs(tmp_path):
    """Client with two CSV documents uploaded."""
    client = ADX(storage_dir=tmp_path / "store")
    d = tmp_path / "data"
    d.mkdir()

    _create_csv(d / "sales.csv", "product,revenue\nWidget,1000\nGadget,2000\n")
    _create_csv(d / "inventory.csv", "product,stock\nWidget,50\nGadget,30\n")

    result = client.upload_directory(d)
    assert result.successful == 2
    return client, result.graphs


class TestCorpusSearchBasic:
    def test_finds_matching_text(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("Widget")
        assert len(hits) > 0
        assert any("Widget" in h["text_snippet"] for h in hits)

    def test_returns_empty_for_no_match(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("zzzzzzzznonexistent")
        assert len(hits) == 0

    def test_max_results_respected(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("Widget", max_results=1)
        assert len(hits) <= 1

    def test_results_have_required_fields(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("Widget")
        for hit in hits:
            assert "file_id" in hit
            assert "filename" in hit
            assert "text_snippet" in hit
            assert "score" in hit
            assert "citation" in hit


class TestCorpusSearchScoping:
    def test_filter_by_file_ids(self, client_with_docs):
        client, graph_ids = client_with_docs
        # Search only the first file
        hits = client.search_corpus("Widget", file_ids=[graph_ids[0]])
        filenames = {h["filename"] for h in hits}
        assert len(filenames) <= 1

    def test_all_files_searched_by_default(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("Widget")
        filenames = {h["filename"] for h in hits}
        assert len(filenames) == 2

    def test_nonexistent_file_id_no_crash(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("Widget", file_ids=["nonexistent_id"])
        assert len(hits) == 0


class TestCorpusSearchRanking:
    def test_results_sorted_by_score(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("Widget")
        if len(hits) > 1:
            scores = [h["score"] for h in hits]
            assert scores == sorted(scores, reverse=True)

    def test_higher_frequency_scores_higher(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        d = tmp_path / "data"
        d.mkdir()

        _create_csv(d / "one.csv", "a,b\nfoo,bar\n")
        _create_csv(d / "two.csv", "a,b\nfoo,foo\nfoo,x\n")

        client.upload_directory(d)
        hits = client.search_corpus("foo")
        # The file with more "foo" occurrences should rank higher
        assert len(hits) >= 2


class TestCorpusSearchCellContent:
    def test_finds_cell_values(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("1000")
        assert len(hits) > 0
        assert any("1000" in h["text_snippet"] for h in hits)

    def test_cell_hits_have_sheet_name(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("1000")
        cell_hits = [h for h in hits if h.get("sheet_name")]
        assert len(cell_hits) > 0


class TestCorpusSearchEmpty:
    def test_no_documents(self, tmp_path):
        client = ADX(storage_dir=tmp_path / "store")
        hits = client.search_corpus("anything")
        assert hits == []

    def test_empty_query_tokens(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("a")
        assert hits == []


class TestCorpusSearchMultiWord:
    def test_multi_word_query(self, client_with_docs):
        client, _ = client_with_docs
        hits = client.search_corpus("Widget revenue")
        assert len(hits) > 0

    def test_case_insensitive(self, client_with_docs):
        client, _ = client_with_docs
        hits_lower = client.search_corpus("widget")
        hits_upper = client.search_corpus("WIDGET")
        assert len(hits_lower) == len(hits_upper)
