---
title: REST API
---

# REST API Reference

Start the server with `docunav serve` (default: `http://localhost:8000`).

## Files

### POST /v1/files

Upload a document.

```bash
curl -X POST http://localhost:8000/v1/files -F "file=@document.pdf"
```

**Response:**
```json
{"id": "doc_abc123", "file_name": "document.pdf", "file_type": "pdf", "status": "ready"}
```

### GET /v1/files/{id}

Get file metadata.

### GET /v1/files

List all uploaded files.

## Inspection

### GET /v1/files/{id}/profile

Profile the document — metadata, type detection, recommended tools.

### GET /v1/files/{id}/structure

Document structure — sections, tables, page outline.

### POST /v1/files/{id}/search

Search the document.

```json
{"query": "payment terms", "max_results": 20}
```

### GET /v1/files/{id}/pages/{page_number}

Get a specific page's text blocks and tables.

### GET /v1/files/{id}/tables

List all tables in the document.

### GET /v1/files/{id}/tables/{table_id}

Get a specific table's contents.

## Spreadsheet Tools

### GET /v1/files/{id}/sheets

List sheets with metadata.

### POST /v1/files/{id}/ranges/read

Read a cell range.

```json
{"sheet": "Summary", "range": "A1:D10", "include_formulas": true}
```

### POST /v1/files/{id}/cells/find

Find cells matching a query.

```json
{"query": "Revenue", "sheet": "Summary"}
```

### POST /v1/files/{id}/formulas/inspect

Inspect a formula's dependencies.

```json
{"sheet": "Summary", "cell": "B10"}
```

## Extraction

### POST /v1/files/{id}/extract

Extract fields using a schema.

```json
{"schema": "invoice"}
```

Or with a custom schema:

```json
{
  "schema": {
    "name": "custom",
    "fields": [
      {"name": "po_number", "type": "string", "required": true}
    ]
  }
}
```

### GET /v1/extractions/{extraction_id}

Retrieve a previous extraction result.

## Validation

### POST /v1/files/{id}/validate

Validate an extraction.

```json
{"extraction_id": "ext_abc123"}
```

## Citations

### GET /v1/files/{id}/citations

Get all citations for a document.

## Export

### POST /v1/files/{id}/export

Export document content.

```json
{"format": "markdown"}
```

Supported formats: `json`, `markdown`, `csv`.

## Health

### GET /health

```json
{"status": "healthy", "version": "0.1.0"}
```
