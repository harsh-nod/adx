---
title: Python SDK
---

# Python SDK Reference

## ADX Client

```python
from adx import ADX

dn = ADX(storage_dir="~/.adx")
```

### Constructor

| Parameter | Type | Default | Description |
|---|---|---|---|
| `storage_dir` | `str` | `~/.adx` | Directory for file and graph storage |

## File Operations

### upload(path)

Upload a file from disk. Returns a document ID.

```python
doc_id = dn.upload("invoice.pdf")
```

### upload_bytes(data, filename)

Upload from bytes.

```python
doc_id = dn.upload_bytes(pdf_bytes, "invoice.pdf")
```

### get_graph(doc_id)

Get the full `DocumentGraph` object.

```python
graph = dn.get_graph(doc_id)
```

### list_files()

List all uploaded documents.

```python
files = dn.list_files()
```

## Inspection Tools

### profile(doc_id)

```python
profile = dn.profile(doc_id)
# Returns: file_name, file_type, page_count, document_type, has_tables, table_count, confidence, recommended_tools
```

### structure(doc_id)

```python
structure = dn.structure(doc_id)
# Returns: sections[], tables[], page_count
```

### search(doc_id, query, max_results=20)

```python
results = dn.search(doc_id, query="total")
# Returns: matches[] with page, snippet, bbox
```

### get_page(doc_id, page_number)

```python
page = dn.get_page(doc_id, page_number=1)
# Returns: text_blocks[], tables[]
```

### get_table(doc_id, table_id)

```python
table = dn.get_table(doc_id, table_id="table_0")
# Returns: headers[], rows[][], markdown, citation
```

### list_sheets(doc_id)

```python
sheets = dn.list_sheets(doc_id)
# Returns: sheets[] with name, rows, cols, hidden, named_ranges
```

### read_range(doc_id, sheet, range, include_formulas=True)

```python
data = dn.read_range(doc_id, sheet="Summary", range="A1:D10")
# Returns: cells[] with address, value, formula, type
```

### find_cells(doc_id, query, sheet=None)

```python
results = dn.find_cells(doc_id, query="Revenue")
# Returns: matches[] with address, value, sheet, formula
```

### inspect_formula(doc_id, sheet, cell)

```python
info = dn.inspect_formula(doc_id, sheet="Summary", cell="B10")
# Returns: formula, computed_value, references, cross_sheet_refs, external_refs
```

## Extraction

### extract(doc_id, schema=None)

```python
extraction = dn.extract(doc_id, schema="invoice")
# Returns: id, schema, fields[] with name, value, confidence, citation
```

### validate(doc_id, extraction_id)

```python
result = dn.validate(doc_id, extraction_id)
# Returns: checks[] with severity, rule, message, fields
```

### get_extraction(doc_id, extraction_id)

```python
extraction = dn.get_extraction(doc_id, extraction_id)
```

## Export

### export(doc_id, format="json")

```python
output = dn.export(doc_id, format="markdown")
```

Formats: `json`, `markdown`, `csv`.
