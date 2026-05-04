---
title: Extraction
---

# Schema-Driven Extraction

ADX extracts structured fields from documents using predefined schemas. Every extracted field includes a confidence score and citation back to the source.

## Built-in Schemas

| Schema | Fields | Use Case |
|---|---|---|
| `invoice` | vendor, invoice_number, date, line_items, subtotal, tax, total, currency | Invoice processing |
| `contract` | parties, effective_date, expiration_date, governing_law, termination_clause | Contract review |
| `financial_model` | revenue, expenses, net_income, assumptions, growth_rate | Financial analysis |
| `table` | headers, rows | Generic table extraction |

## Using a Schema

```python
from adx import ADX

dn = ADX()
doc_id = dn.upload("invoice.pdf")

# Extract with a built-in schema
extraction = dn.extract(doc_id, schema="invoice")

# Each field has a value, confidence, and citation
for field in extraction["fields"]:
    print(f"{field['name']}: {field['value']}")
    print(f"  confidence: {field['confidence']}")
    print(f"  citation: page {field['citation']['page']}")
```

## Auto-Detection

If no schema is specified, ADX uses the document type detected during profiling:

```python
# Auto-detects schema from document type
extraction = dn.extract(doc_id)
```

## Custom Schemas

Define custom extraction schemas using JSON Schema format:

```python
schema = {
    "name": "purchase_order",
    "fields": [
        {"name": "po_number", "type": "string", "required": True},
        {"name": "vendor", "type": "string", "required": True},
        {"name": "total", "type": "number", "required": True},
        {"name": "delivery_date", "type": "string", "required": False}
    ]
}

extraction = dn.extract(doc_id, schema=schema)
```

## How Extraction Works

1. **Label search** — finds field labels in the document (e.g., "Invoice Number", "Invoice #", "Inv No.")
2. **Value extraction** — reads the adjacent text or cell value
3. **Type coercion** — converts to the expected type (string, number, integer)
4. **Citation creation** — links each value to its source location
5. **Confidence scoring** — based on label match quality and parser confidence

For PDFs, extraction uses text proximity — finding values near label text blocks. For spreadsheets, it uses cell adjacency — finding values in cells next to label cells.

## Field-Level Citations

Every extracted field includes a citation:

```json
{
  "name": "total",
  "value": 4250.00,
  "confidence": 0.95,
  "citation": {
    "type": "page",
    "page": 3,
    "bbox": [72, 680, 540, 700],
    "text": "Total: $4,250.00"
  }
}
```

For spreadsheets, citations reference cell addresses:

```json
{
  "name": "revenue",
  "value": 1500000,
  "confidence": 0.9,
  "citation": {
    "type": "cell",
    "sheet": "Summary",
    "cell": "B5",
    "text": "1500000"
  }
}
```
