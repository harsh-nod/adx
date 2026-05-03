# DocuNav

Agent-native document intelligence layer. Wraps best-in-class document parsers and exposes structured, citeable, inspectable document state to AI agents.

## What It Does

DocuNav is **not** a parser. It is an orchestration layer that:

1. **Wraps** parsers (PyMuPDF, openpyxl, csv) behind a uniform interface
2. **Builds** a canonical `DocumentGraph` from any supported format
3. **Exposes** 9 read-only agent tools for inspection and search
4. **Extracts** fields using built-in schemas with field-level citations
5. **Validates** results with rule-based checks

## Install

```bash
pip install docunav
```

## Quick Start

```python
from docunav import DocuNav

dn = DocuNav()
doc_id = dn.upload("invoice.pdf")

# Profile the document
profile = dn.profile(doc_id)

# Extract with a built-in schema
extraction = dn.extract(doc_id, schema="invoice")

# Validate
result = dn.validate(doc_id, extraction["id"])
```

## Agent Tools

| Tool | Description |
|---|---|
| `profile_document` | File metadata, type detection, recommended tools |
| `list_structure` | Sections, tables, page outline |
| `search_document` | Full-text search with citations |
| `get_page` | Page text blocks and tables |
| `get_table` | Table rows with headers |
| `list_sheets` | Spreadsheet sheet metadata |
| `read_range` | Cell range with formulas |
| `find_cells` | Search cells by value |
| `inspect_formula` | Trace formula dependencies |

## Built-in Schemas

- `invoice` — vendor, line items, totals, tax
- `contract` — parties, dates, governing law
- `financial_model` — revenue, expenses, assumptions
- `table` — generic table extraction

## REST API

```bash
docunav serve
curl -X POST http://localhost:8000/v1/files -F "file=@invoice.pdf"
curl http://localhost:8000/v1/files/{id}/profile
```

## CLI

```bash
docunav upload invoice.pdf
docunav profile <id>
docunav extract <id> --schema invoice
docunav validate <id> --extraction <eid>
```

## Supported Formats

| Format | Parser | Features |
|---|---|---|
| PDF | PyMuPDF | Text blocks, tables, bounding boxes, sections |
| Excel (.xlsx) | openpyxl | Sheets, formulas, hidden content, named ranges |
| CSV | stdlib | Dialect sniffing, encoding detection |

## Documentation

https://harsh-nod.github.io/adx/

## License

MIT
