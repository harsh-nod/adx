---
title: Corpus Search
---

# Corpus Search

Search across all uploaded documents to find relevant content across your entire collection.

## Quick Start

```python
from adx import ADX

dn = ADX()

# Upload some documents
dn.upload("report_q1.pdf")
dn.upload("report_q2.pdf")
dn.upload("budget.xlsx")

# Search across all of them
hits = dn.search_corpus("revenue forecast")
for hit in hits:
    print(f"{hit['filename']} — {hit['text_snippet'][:80]}...")
    print(f"  Location: {hit['citation']}")
    print(f"  Score: {hit['score']}")
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | required | Search query (tokenized, case-insensitive) |
| `file_ids` | `list[str] \| None` | `None` | Limit search to specific files (None = all) |
| `max_results` | `int` | `20` | Maximum results to return |

## Search Result

Each hit includes:

| Field | Description |
|---|---|
| `file_id` | Source document ID |
| `filename` | Source filename |
| `text_snippet` | Matching text (up to 200 chars) |
| `page_number` | Page number (PDFs/DOCX) or `None` |
| `sheet_name` | Sheet name (spreadsheets) or `None` |
| `score` | Relevance score (token hit count) |
| `citation` | Human-readable source reference |

Results are ranked by score (highest first).

## Filtering by File

Search only within specific documents:

```python
hits = dn.search_corpus(
    "total expenses",
    file_ids=["abc123", "def456"],
    max_results=10,
)
```

## Async Usage

```python
from adx import AsyncADX

async def search():
    dn = AsyncADX()
    hits = await dn.search_corpus("quarterly revenue")
    return hits
```

## REST API

```bash
curl -X POST http://localhost:8000/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "revenue forecast", "max_results": 20}'
```

## vs. Single-Document Search

| Feature | `search(file_id, query)` | `search_corpus(query)` |
|---|---|---|
| Scope | One document | All documents |
| Speed | Fast | Scales with corpus size |
| Use case | Drill into a known document | Find which documents are relevant |
