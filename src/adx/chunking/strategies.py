"""Chunking strategies for DocumentGraph."""

from __future__ import annotations

from adx.chunking.models import Chunk, ChunkingConfig
from adx.models.document import (
    Citation,
    CitationType,
    DocumentGraph,
    Section,
    TextBlockType,
)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def _build_section_path(sections: list[Section], block_text: str) -> list[str]:
    """Find the section path for a heading text."""
    for section in sections:
        if section.title == block_text.strip():
            path = [section.title]
            parent_id = section.parent_section_id
            while parent_id:
                parent = next((s for s in sections if s.id == parent_id), None)
                if parent:
                    path.insert(0, parent.title)
                    parent_id = parent.parent_section_id
                else:
                    break
            return path
    return []


def _current_section_path(sections: list[Section], page_number: int) -> list[str]:
    """Get the deepest section path active at a given page."""
    active = [
        s for s in sections
        if s.start_page is not None
        and s.start_page <= page_number
        and (s.end_page is None or s.end_page >= page_number)
    ]
    if not active:
        return []
    # Return the deepest one
    deepest = max(active, key=lambda s: s.heading_level)
    path = [deepest.title]
    parent_id = deepest.parent_section_id
    while parent_id:
        parent = next((s for s in sections if s.id == parent_id), None)
        if parent:
            path.insert(0, parent.title)
            parent_id = parent.parent_section_id
        else:
            break
    return path


def fixed_size_chunks(graph: DocumentGraph, config: ChunkingConfig) -> list[Chunk]:
    """Split document text into fixed-size chunks with overlap."""
    full_text = graph.get_all_text()
    if not full_text.strip():
        return []

    chunks: list[Chunk] = []
    max_chars = config.max_chunk_size * 4  # Convert token estimate to chars
    overlap_chars = config.overlap * 4
    start = 0

    while start < len(full_text):
        end = min(start + max_chars, len(full_text))
        chunk_text = full_text[start:end].strip()
        if chunk_text:
            page_nums = []
            for page in graph.pages:
                if page.full_text and any(
                    line in chunk_text for line in page.full_text.split("\n")[:3] if line.strip()
                ):
                    page_nums.append(page.page_number)

            citations = []
            if page_nums:
                citations.append(Citation(
                    document_id=graph.document.id,
                    citation_type=CitationType.PAGE,
                    page_number=page_nums[0],
                    text_snippet=chunk_text[:200],
                ))

            chunks.append(Chunk(
                text=chunk_text,
                chunk_type="text",
                citations=citations,
                page_numbers=page_nums or [],
                token_count=_estimate_tokens(chunk_text),
            ))

        step = max_chars - overlap_chars
        if step <= 0:
            step = max_chars
        start += step

    return chunks


def section_aware_chunks(graph: DocumentGraph, config: ChunkingConfig) -> list[Chunk]:
    """Split document by sections, breaking at heading boundaries."""
    chunks: list[Chunk] = []
    current_text_parts: list[str] = []
    current_pages: list[int] = set()
    current_section_path: list[str] = []
    current_citations: list[Citation] = []
    max_chars = config.max_chunk_size * 4

    def _flush():
        text = "\n".join(current_text_parts).strip()
        if text:
            chunks.append(Chunk(
                text=text,
                chunk_type="text",
                citations=list(current_citations),
                section_path=list(current_section_path),
                page_numbers=sorted(current_pages),
                token_count=_estimate_tokens(text),
            ))

    for page in sorted(graph.pages, key=lambda p: p.page_number):
        for block in sorted(page.text_blocks, key=lambda b: b.reading_order_index):
            if block.block_type in (TextBlockType.HEADER, TextBlockType.FOOTER, TextBlockType.PAGE_NUMBER):
                continue

            if block.block_type == TextBlockType.HEADING:
                _flush()
                current_text_parts = []
                current_pages = set()
                current_citations = []
                current_section_path = _build_section_path(graph.sections, block.text) or [block.text]

            current_text_parts.append(block.text)
            current_pages.add(page.page_number)
            current_citations.append(Citation(
                document_id=graph.document.id,
                citation_type=CitationType.PAGE,
                page_number=page.page_number,
                text_snippet=block.text[:200],
            ))

            # Check size and split if needed
            current_len = sum(len(p) for p in current_text_parts)
            if current_len >= max_chars:
                _flush()
                # Keep overlap
                overlap_text = current_text_parts[-1] if current_text_parts else ""
                current_text_parts = [overlap_text] if overlap_text else []
                current_citations = current_citations[-1:] if current_citations else []

    _flush()

    # Tables as chunks
    if config.include_tables:
        chunks.extend(table_as_chunk(graph, config))

    return chunks


def table_as_chunk(graph: DocumentGraph, config: ChunkingConfig) -> list[Chunk]:
    """Emit each table as its own chunk."""
    chunks: list[Chunk] = []

    for page in graph.pages:
        for table in page.tables:
            md = table.to_markdown()
            if md:
                section_path = _current_section_path(graph.sections, page.page_number)
                chunks.append(Chunk(
                    text=md,
                    chunk_type="table",
                    citations=[Citation(
                        document_id=graph.document.id,
                        citation_type=CitationType.TABLE,
                        page_number=page.page_number,
                        text_snippet=md[:200],
                    )],
                    section_path=section_path,
                    page_numbers=[page.page_number],
                    token_count=_estimate_tokens(md),
                ))

    if graph.workbook:
        for sheet in graph.workbook.sheets:
            for table in sheet.tables:
                md = table.to_markdown()
                if md:
                    chunks.append(Chunk(
                        text=md,
                        chunk_type="table",
                        citations=[Citation(
                            document_id=graph.document.id,
                            citation_type=CitationType.TABLE,
                            sheet_name=sheet.name,
                            text_snippet=md[:200],
                        )],
                        sheet_name=sheet.name,
                        page_numbers=[],
                        token_count=_estimate_tokens(md),
                    ))

    return chunks


def chunk_document(graph: DocumentGraph, config: ChunkingConfig | None = None) -> list[Chunk]:
    """Chunk a document using the specified strategy."""
    if config is None:
        config = ChunkingConfig()

    strategies = {
        "fixed_size": fixed_size_chunks,
        "section_aware": section_aware_chunks,
        "table_only": table_as_chunk,
    }

    strategy_fn = strategies.get(config.strategy)
    if strategy_fn is None:
        raise ValueError(f"Unknown chunking strategy: {config.strategy}. "
                         f"Available: {', '.join(strategies.keys())}")

    return strategy_fn(graph, config)
