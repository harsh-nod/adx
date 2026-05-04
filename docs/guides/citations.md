---
title: Citations
---

# Citations

Every value ADX returns traces back to a specific location in the source document. Citations are the provenance layer that lets agents (and humans) verify extracted data.

## Citation Types

| Type | Source | Fields |
|---|---|---|
| `page` | PDF text block | `page`, `bbox`, `text` |
| `table` | PDF table cell | `page`, `bbox`, `table_id`, `row`, `col` |
| `cell` | Spreadsheet cell | `sheet`, `cell`, `text` |
| `range` | Spreadsheet range | `sheet`, `range`, `text` |
| `formula` | Spreadsheet formula | `sheet`, `cell`, `formula` |

## Where Citations Appear

### In Text Blocks

Every text block extracted from a PDF includes a citation:

```json
{
  "text": "Payment is due within 30 days.",
  "type": "paragraph",
  "citation": {
    "type": "page",
    "page": 2,
    "bbox": [72, 450, 540, 470]
  }
}
```

### In Extracted Fields

Every field from `extract()` includes a citation:

```json
{
  "name": "total",
  "value": 4250.00,
  "citation": {
    "type": "page",
    "page": 3,
    "bbox": [72, 680, 540, 700],
    "text": "Total: $4,250.00"
  }
}
```

### In Search Results

Search matches include location information:

```json
{
  "query": "payment terms",
  "matches": [
    {
      "page": 2,
      "snippet": "...Payment is due within 30 days of invoice date...",
      "bbox": [72, 450, 540, 470]
    }
  ]
}
```

### In Formula Inspection

Formula references are cited back to their source cells:

```json
{
  "formula": "=SUM(B2:B9)",
  "computed_value": 125000,
  "references": [
    {"type": "range", "sheet": "Revenue", "range": "B2:B9"}
  ]
}
```

## Retrieving Citations

Use the citations endpoint to get all citations for a document:

```bash
curl http://localhost:8000/v1/files/{id}/citations
```

Or access citations through the Python SDK:

```python
graph = dn.get_graph(doc_id)
for citation in graph.citations:
    print(f"  [{citation.type}] page={citation.page} text={citation.text[:50]}")
```

## Why Citations Matter

- **Verifiability** — agents can prove where data came from
- **Auditability** — humans can spot-check extracted values
- **Confidence** — low-confidence extractions can be traced and reviewed
- **Debugging** — when extraction is wrong, citations show what the parser actually saw
