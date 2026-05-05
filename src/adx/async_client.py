"""Async interface for ADX, mirroring the synchronous ADX client."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from adx.client import ADX
from adx.models.document import BatchResult, DocumentGraph, Extraction, ValidationResult


class AsyncADX:
    """Async wrapper around the ADX client.

    CPU-bound parsing is dispatched to a thread pool via run_in_executor.
    """

    def __init__(
        self,
        storage_dir: str | Path | None = None,
        api_key: str | None = None,
        max_workers: int | None = None,
    ) -> None:
        self._client = ADX(storage_dir=storage_dir, api_key=api_key)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: fn(*args, **kwargs))

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    async def upload(self, file_path: str | Path) -> DocumentGraph:
        return await self._run(self._client.upload, file_path)

    async def upload_bytes(self, data: bytes, filename: str) -> DocumentGraph:
        return await self._run(self._client.upload_bytes, data, filename)

    async def get_graph(self, file_id: str) -> DocumentGraph | None:
        return await self._run(self._client.get_graph, file_id)

    async def list_files(self) -> list[str]:
        return await self._run(self._client.list_files)

    async def to_markdown(self, file_id: str) -> str:
        return await self._run(self._client.to_markdown, file_id)

    async def upload_directory(
        self,
        path: str | Path,
        recursive: bool = True,
        extensions: set[str] | None = None,
    ) -> BatchResult:
        return await self._run(self._client.upload_directory, path, recursive, extensions)

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    async def profile(self, file_id: str) -> dict[str, Any]:
        return await self._run(self._client.profile, file_id)

    async def search(self, file_id: str, query: str, max_results: int = 20) -> dict[str, Any]:
        return await self._run(self._client.search, file_id, query, max_results)

    async def search_corpus(
        self,
        query: str,
        file_ids: list[str] | None = None,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        return await self._run(self._client.search_corpus, query, file_ids, max_results)

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    async def chunk(
        self,
        file_id: str,
        strategy: str = "section_aware",
        max_chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[Any]:
        return await self._run(self._client.chunk, file_id, strategy, max_chunk_size, overlap)

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    async def extract(
        self,
        file_id: str,
        schema: str | dict[str, Any] | None = None,
        instructions: str | None = None,
    ) -> Extraction:
        return await self._run(self._client.extract, file_id, schema, instructions)

    async def validate(self, extraction_id: str) -> list[ValidationResult]:
        return await self._run(self._client.validate, extraction_id)

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------

    async def upload_many(self, file_paths: list[str | Path]) -> list[DocumentGraph]:
        """Upload multiple files concurrently."""
        tasks = [self.upload(fp) for fp in file_paths]
        return await asyncio.gather(*tasks)
