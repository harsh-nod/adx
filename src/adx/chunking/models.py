"""Chunking data models."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from adx.models.document import Citation


def _chunk_id() -> str:
    return f"chunk-{uuid.uuid4().hex[:12]}"


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""

    strategy: str = "section_aware"
    max_chunk_size: int = 1000
    overlap: int = 200
    include_tables: bool = True


class Chunk(BaseModel):
    """A chunk of document content with provenance."""

    id: str = Field(default_factory=_chunk_id)
    text: str = ""
    chunk_type: str = "text"
    citations: list[Citation] = Field(default_factory=list)
    section_path: list[str] = Field(default_factory=list)
    page_numbers: list[int] = Field(default_factory=list)
    sheet_name: str | None = None
    token_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
