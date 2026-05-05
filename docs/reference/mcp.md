---
title: MCP Tools
---

# MCP Tools

ADX provides a fully implemented MCP (Model Context Protocol) server, making all document tools available to Claude and other MCP-compatible AI agents.

## Setup

Add ADX to your MCP client configuration:

```json
{
  "mcpServers": {
    "adx": {
      "command": "adx",
      "args": ["mcp"],
      "env": {
        "ADX_STORAGE_DIR": "/path/to/storage"
      }
    }
  }
}
```

## Available Tools

| Tool | Description | Required Params |
|---|---|---|
| `adx_upload` | Upload and process a document file | `file_path` |
| `adx_profile` | Profile a document: metadata, type, confidence | `file_id` |
| `adx_structure` | Get document structure: sections, tables, pages | `file_id` |
| `adx_search` | Full-text search within a single document | `file_id`, `query` |
| `adx_search_corpus` | Search across all uploaded documents | `query` |
| `adx_get_page` | Get text and tables from a specific page | `file_id`, `page_number` |
| `adx_get_table` | Get a specific table by ID | `file_id`, `table_id` |
| `adx_to_markdown` | Export a document as markdown | `file_id` |
| `adx_chunk` | Chunk a document for retrieval pipelines | `file_id` |
| `adx_list_sheets` | List workbook sheets in a spreadsheet | `file_id` |

## Tool Details

### adx_upload

Upload and process a document file. Returns file ID and metadata.

```json
{
  "file_path": "/path/to/document.pdf"
}
```

### adx_profile

Profile a document — file type, page/sheet count, detected document types, confidence scores, and recommended next tools.

```json
{
  "file_id": "abc123"
}
```

### adx_search

Search text and cells within a single document.

```json
{
  "file_id": "abc123",
  "query": "revenue forecast",
  "max_results": 20
}
```

### adx_search_corpus

Search across all uploaded documents. Useful for finding information across a collection.

```json
{
  "query": "total revenue",
  "max_results": 20
}
```

### adx_chunk

Chunk a document for retrieval pipelines (RAG).

```json
{
  "file_id": "abc123",
  "strategy": "section_aware",
  "max_chunk_size": 1000
}
```

Strategies: `fixed_size`, `section_aware`, `table_only`.

## Python Usage

```python
from adx.mcp.server import create_mcp_server

server = create_mcp_server(storage_dir="./data")
```

The MCP server wraps the same core functions as the REST API and Python SDK, ensuring consistent behavior across all interfaces.
