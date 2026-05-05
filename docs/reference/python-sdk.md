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
| `storage_dir` | `str \| Path \| None` | `./adx_storage` | Directory for file and graph storage |
| `api_key` | `str \| None` | `None` | Optional API key |

## File Operations

### upload(path)

Upload a file from disk. Returns a `DocumentGraph`.

```python
graph = dn.upload("invoice.pdf")
doc_id = graph.document.id
```

### upload_bytes(data, filename)

Upload from bytes.

```python
graph = dn.upload_bytes(pdf_bytes, "invoice.pdf")
```

### get_graph(file_id)

Get the full `DocumentGraph` object.

```python
graph = dn.get_graph(file_id)
```

### list_files()

List all uploaded document IDs.

```python
file_ids = dn.list_files()
```

### to_markdown(file_id)

Render a document graph as markdown.

```python
md = dn.to_markdown(file_id)
```

### upload_directory(path, recursive=True, extensions=None)

Upload all supported files in a directory.

```python
result = dn.upload_directory("./documents/", recursive=True)
# result.total_files, result.successful, result.failed, result.graphs, result.errors
```

## Inspection Tools

### profile(file_id)

```python
profile = dn.profile(file_id)
# Returns: file_name, file_type, page_count, document_type, has_tables, table_count, confidence, recommended_tools
```

### structure(file_id)

```python
structure = dn.structure(file_id)
# Returns: sections[], tables[], page_count
```

### search(file_id, query, max_results=20)

```python
results = dn.search(file_id, query="total")
# Returns: matches[] with page, snippet, bbox
```

### get_page(file_id, page_number)

```python
page = dn.get_page(file_id, page_number=1)
# Returns: text_blocks[], tables[]
```

### get_table(file_id, table_id)

```python
table = dn.get_table(file_id, table_id="table_0")
# Returns: headers[], rows[][], markdown, citation
```

### list_sheets(file_id)

```python
sheets = dn.list_sheets(file_id)
# Returns: sheets[] with name, rows, cols, hidden, named_ranges
```

### read_range(file_id, sheet, range)

```python
data = dn.read_range(file_id, sheet_name="Summary", cell_range="A1:D10")
# Returns: cells[] with address, value, formula, type
```

### find_cells(file_id, query, sheet_name=None)

```python
results = dn.find_cells(file_id, query="Revenue")
# Returns: matches[] with address, value, sheet, formula
```

### inspect_formula(file_id, sheet, cell)

```python
info = dn.inspect_formula(file_id, sheet_name="Summary", cell_address="B10")
# Returns: formula, computed_value, references, cross_sheet_refs, external_refs
```

## Corpus Search

### search_corpus(query, file_ids=None, max_results=20)

Search across all stored document graphs.

```python
hits = dn.search_corpus("revenue forecast")
for hit in hits:
    print(hit["filename"], hit["text_snippet"], hit["citation"])
```

## Chunking

### chunk(file_id, strategy="section_aware", max_chunk_size=1000, overlap=200)

Chunk a document for retrieval pipelines.

```python
chunks = dn.chunk(file_id, strategy="section_aware", max_chunk_size=1000, overlap=200)
for chunk in chunks:
    print(chunk.id, chunk.text[:100], chunk.token_count)
```

Strategies: `fixed_size`, `section_aware`, `table_only`.

## Extraction

### extract(file_id, schema=None, instructions=None)

```python
extraction = dn.extract(file_id, schema="invoice")
# Returns: Extraction with id, schema, fields[] (name, value, confidence, citations)
```

Accepts a schema name (string), `ExtractionSchema` object, or JSON Schema dict:

```python
extraction = dn.extract(file_id, schema={
    "type": "object",
    "properties": {
        "company": {"type": "string", "description": "Company name"},
        "revenue": {"type": "number", "minimum": 0},
    },
    "required": ["company"],
})
```

### validate(extraction_id)

```python
results = dn.validate(extraction_id)
# Returns: list[ValidationResult] with severity, rule, message, fields
```

### get_extraction(extraction_id)

```python
extraction = dn.get_extraction(extraction_id)
```

## Export

### export(extraction_id, format="json")

```python
output = dn.export(extraction_id, format="markdown")
```

Formats: `json`, `markdown`, `csv`.

---

## AsyncADX Client

Async wrapper around the ADX client. CPU-bound parsing is dispatched to a thread pool.

```python
from adx import AsyncADX

async_dn = AsyncADX(storage_dir="~/.adx", max_workers=4)
```

### Constructor

| Parameter | Type | Default | Description |
|---|---|---|---|
| `storage_dir` | `str \| Path \| None` | `./adx_storage` | Directory for file and graph storage |
| `api_key` | `str \| None` | `None` | Optional API key |
| `max_workers` | `int \| None` | `None` | Thread pool size (defaults to Python's default) |

### Methods

All methods mirror the synchronous `ADX` client but return coroutines:

```python
import asyncio

async def main():
    dn = AsyncADX()

    # Upload
    graph = await dn.upload("invoice.pdf")
    graph = await dn.upload_bytes(data, "invoice.pdf")

    # Inspect
    profile = await dn.profile(graph.document.id)
    results = await dn.search(graph.document.id, "total")

    # Corpus search
    hits = await dn.search_corpus("revenue")

    # Chunk
    chunks = await dn.chunk(graph.document.id, strategy="section_aware")

    # Extract
    extraction = await dn.extract(graph.document.id, schema="invoice")
    validations = await dn.validate(extraction.id)

    # Batch upload (concurrent)
    graphs = await dn.upload_many(["a.pdf", "b.pdf", "c.xlsx"])

asyncio.run(main())
```

### upload_many(file_paths)

Upload multiple files concurrently using `asyncio.gather`.

```python
graphs = await dn.upload_many(["report.pdf", "model.xlsx", "contract.docx"])
```
