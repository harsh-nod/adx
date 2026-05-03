---
title: Quickstart
---

# Quickstart

Get started with DocuNav in five minutes.

## Install

```bash
pip install docunav
```

For LLM-powered extraction (optional):

```bash
pip install docunav[llm]
```

## Upload a Document

```python
from docunav import DocuNav

dn = DocuNav()
doc_id = dn.upload("invoice.pdf")
print(f"Document ID: {doc_id}")
```

## Profile It

```python
profile = dn.profile(doc_id)
print(profile)
```

```json
{
  "file_name": "invoice.pdf",
  "file_type": "pdf",
  "page_count": 3,
  "document_type": "invoice",
  "has_tables": true,
  "table_count": 2,
  "confidence": {"overall": 0.92},
  "recommended_tools": ["get_table", "search_document"]
}
```

## Explore the Structure

```python
structure = dn.structure(doc_id)
for section in structure["sections"]:
    print(f"  {section['title']} (page {section['start_page']})")
for table in structure["tables"]:
    print(f"  Table: {table['id']} — {table['row_count']}x{table['col_count']}")
```

## Search

```python
results = dn.search(doc_id, query="total")
for hit in results["matches"]:
    print(f"  Page {hit['page']}: {hit['snippet']}")
```

## Extract Fields

```python
extraction = dn.extract(doc_id, schema="invoice")
for field in extraction["fields"]:
    print(f"  {field['name']}: {field['value']} (confidence: {field['confidence']})")
```

Built-in schemas: `invoice`, `contract`, `financial_model`, `table`.

## Validate

```python
result = dn.validate(doc_id, extraction["id"])
for check in result["checks"]:
    print(f"  [{check['severity']}] {check['rule']}: {check['message']}")
```

Validation checks include:
- Required fields present
- Type correctness
- Arithmetic verification (e.g., subtotal + tax = total)
- Citation provenance

## Export

```python
# Export as markdown
md = dn.export(doc_id, format="markdown")

# Export as JSON
data = dn.export(doc_id, format="json")

# Export as CSV (tables only)
csv_data = dn.export(doc_id, format="csv")
```

## REST API

Start the server and use HTTP endpoints:

```bash
docunav serve

# Upload
curl -X POST http://localhost:8000/v1/files -F "file=@invoice.pdf"

# Profile
curl http://localhost:8000/v1/files/{id}/profile

# Extract
curl -X POST http://localhost:8000/v1/files/{id}/extract \
  -H "Content-Type: application/json" \
  -d '{"schema": "invoice"}'
```

## CLI

```bash
docunav upload invoice.pdf
docunav profile <id>
docunav search <id> --query "total amount"
docunav extract <id> --schema invoice
docunav validate <id> --extraction <eid>
```

## Next Steps

- [Agent Tools](../guides/agent-tools) — full reference for all nine tools
- [PDF Guide](../guides/pdf-processing) — PDF-specific features
- [Excel Guide](../guides/excel-processing) — spreadsheet navigation
- [Examples](../examples/) — real-world extraction workflows
