---
title: Invoice Extraction
---

# Invoice Extraction

This example extracts structured data from a PDF invoice and validates the results.

## Upload

```python
from adx import ADX

dn = ADX()
doc_id = dn.upload("invoice.pdf")
```

## Profile

```python
profile = dn.profile(doc_id)
# {
#   "document_type": "invoice",
#   "page_count": 2,
#   "table_count": 1,
#   "recommended_tools": ["get_table", "search_document"]
# }
```

## Explore Tables

```python
structure = dn.structure(doc_id)
table = dn.get_table(doc_id, structure["tables"][0]["id"])
print(table["markdown"])
```

```
| Item          | Qty | Unit Price | Amount   |
|---------------|-----|------------|----------|
| Widget A      | 10  | $25.00     | $250.00  |
| Widget B      | 5   | $50.00     | $250.00  |
| Service Fee   | 1   | $500.00    | $500.00  |
```

## Extract

```python
extraction = dn.extract(doc_id, schema="invoice")
for field in extraction["fields"]:
    print(f"{field['name']}: {field['value']}")
```

```
vendor: Acme Corp
invoice_number: INV-2024-001
date: 2024-03-15
subtotal: 1000.00
tax: 80.00
total: 1080.00
currency: USD
```

## Validate

```python
result = dn.validate(doc_id, extraction["id"])
for check in result["checks"]:
    print(f"[{check['severity']}] {check['rule']}: {check['message']}")
```

```
[info] required_field: All required fields present
[info] arithmetic: subtotal (1000.00) + tax (80.00) = total (1080.00) ✓
```

The arithmetic validator checks that `subtotal + tax = total`. If the values don't add up, it reports an error with the difference.

## CLI Workflow

```bash
adx upload invoice.pdf
# → doc_abc123

adx profile doc_abc123
adx extract doc_abc123 --schema invoice
# → ext_def456

adx validate doc_abc123 --extraction ext_def456
adx export doc_abc123 --format json
```
