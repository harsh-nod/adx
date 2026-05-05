---
title: Chunking
---

# Chunking

ADX provides document chunking for retrieval-augmented generation (RAG) pipelines. Chunks preserve citations back to source pages and sections.

## Quick Start

```python
from adx import ADX

dn = ADX()
graph = dn.upload("report.pdf")
chunks = dn.chunk(graph.document.id, strategy="section_aware")

for chunk in chunks:
    print(chunk.text[:100], f"({chunk.token_count} tokens)")
```

## Strategies

### section_aware (default)

Splits at section boundaries detected from document headings. Chunks respect the logical structure of the document.

```python
chunks = dn.chunk(file_id, strategy="section_aware", max_chunk_size=1000, overlap=200)
```

### fixed_size

Splits text into fixed-size chunks by token count with configurable overlap.

```python
chunks = dn.chunk(file_id, strategy="fixed_size", max_chunk_size=500, overlap=100)
```

### table_only

Extracts only table content as chunks — useful when you only need structured data.

```python
chunks = dn.chunk(file_id, strategy="table_only")
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `strategy` | `str` | `"section_aware"` | Chunking strategy |
| `max_chunk_size` | `int` | `1000` | Maximum tokens per chunk |
| `overlap` | `int` | `200` | Token overlap between chunks |

## Chunk Object

Each chunk includes:

| Field | Description |
|---|---|
| `id` | Unique chunk identifier |
| `text` | Chunk text content |
| `chunk_type` | Type: `section`, `fixed`, `table` |
| `section_path` | Heading hierarchy path (section_aware only) |
| `page_numbers` | Source page numbers |
| `sheet_name` | Source sheet (spreadsheets only) |
| `token_count` | Estimated token count |
| `citations` | Source citations with page/bbox references |

## REST API

```bash
curl -X POST http://localhost:8000/v1/files/{file_id}/chunks \
  -H "Content-Type: application/json" \
  -d '{"strategy": "section_aware", "max_chunk_size": 1000, "overlap": 200}'
```

## MCP Tool

The `adx_chunk` tool is available via MCP:

```json
{
  "file_id": "abc123",
  "strategy": "section_aware",
  "max_chunk_size": 1000
}
```
