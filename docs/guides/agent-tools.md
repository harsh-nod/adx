---
title: Agent Tools
---

# Agent Tools

DocuNav exposes nine read-only, deterministic tools designed for AI agent consumption. Every tool returns structured JSON with citations.

## Design Principles

- **Read-only**: No tool modifies the document. Agents explore safely.
- **Deterministic**: Same input, same output. No randomness.
- **Structured**: JSON responses, not free text. Agents parse, not guess.
- **Citeable**: Every result traces back to a page, cell, or bounding box.
- **Composable**: Tools suggest next steps. `profile` recommends tools for the document type.

## Tool Reference

### profile_document

Returns file metadata, detected document type, and recommended next tools.

```python
profile = dn.profile(doc_id)
```

**Returns:**
- `file_name`, `file_type`, `file_size`
- `page_count` or `sheet_count`
- `document_type` — auto-detected: `invoice`, `contract`, `financial_model`, `report`, `general`
- `has_tables`, `table_count`
- `confidence` — overall parsing confidence
- `recommended_tools` — what to call next based on document type

### list_structure

Returns the document outline: headings, sections, and table locations.

```python
structure = dn.structure(doc_id)
```

**Returns:**
- `sections[]` — title, start/end page, depth
- `tables[]` — id, page, row/column counts, header row
- `page_count`

### search_document

Full-text search across the document. Returns matches with page/cell location and context.

```python
results = dn.search(doc_id, query="payment terms")
```

**Parameters:**
- `query` — search string
- `max_results` — limit (default: 20)

**Returns:**
- `matches[]` — page, snippet, location (bounding box or cell reference)

### get_page

Retrieve all text blocks and tables on a specific page.

```python
page = dn.get_page(doc_id, page_number=2)
```

**Returns:**
- `text_blocks[]` — text, type (heading/paragraph/header/footer), bounding box
- `tables[]` — table summaries on this page

### get_table

Retrieve a specific table's contents as structured rows.

```python
table = dn.get_table(doc_id, table_id="table_0")
```

**Returns:**
- `headers[]` — column headers
- `rows[][]` — cell values
- `markdown` — pre-rendered markdown table
- `citation` — page, bounding box

### list_sheets

List all sheets in a spreadsheet with metadata.

```python
sheets = dn.list_sheets(doc_id)
```

**Returns:**
- `sheets[]` — name, index, row/column counts, hidden status, named ranges

### read_range

Read a cell range from a spreadsheet.

```python
data = dn.read_range(doc_id, sheet="Summary", range="A1:D10")
```

**Parameters:**
- `sheet` — sheet name
- `range` — cell range (e.g., `A1:D10`)
- `include_formulas` — include formula text (default: true)

**Returns:**
- `cells[]` — address, value, formula, type, hidden status

### find_cells

Search for cells matching a value or pattern.

```python
cells = dn.find_cells(doc_id, query="Revenue", sheet="Summary")
```

**Parameters:**
- `query` — search string
- `sheet` — optional sheet filter

**Returns:**
- `matches[]` — address, value, sheet, formula

### inspect_formula

Trace a formula's dependencies and precedents.

```python
info = dn.inspect_formula(doc_id, sheet="Summary", cell="B10")
```

**Returns:**
- `formula` — the formula text
- `computed_value` — calculated result
- `references` — cells and ranges referenced
- `cross_sheet_refs` — references to other sheets
- `external_refs` — references to external workbooks

## Tool Chaining

Tools are designed to compose naturally. A typical agent workflow:

1. `profile_document` — understand what you're working with
2. `list_structure` — find tables and sections
3. `get_table` or `read_range` — drill into specific data
4. `search_document` — find specific values
5. `extract` — pull structured fields with a schema
6. `validate` — verify extraction correctness

The `recommended_tools` field in `profile_document` guides this flow automatically.
