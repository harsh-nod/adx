---
title: Validation
---

# Validation

ADX validates extractions with rule-based checks. Validation catches missing fields, type errors, arithmetic inconsistencies, and missing citations.

## Running Validation

```python
from adx import ADX

dn = ADX()
doc_id = dn.upload("invoice.pdf")
extraction = dn.extract(doc_id, schema="invoice")
result = dn.validate(doc_id, extraction["id"])

for check in result["checks"]:
    print(f"[{check['severity']}] {check['rule']}: {check['message']}")
```

## Validation Rules

### Required Fields

Checks that all required fields in the schema have non-null values.

```json
{"severity": "error", "rule": "required_field",
 "message": "Required field 'invoice_number' is missing",
 "fields": ["invoice_number"]}
```

### Type Checks

Verifies extracted values match their expected types.

```json
{"severity": "error", "rule": "type_check",
 "message": "Field 'total' expected number, got string",
 "fields": ["total"]}
```

### Citation Checks

Ensures every extracted field has a citation back to the source document.

```json
{"severity": "warning", "rule": "citation_missing",
 "message": "Field 'vendor' has no citation",
 "fields": ["vendor"]}
```

### Confidence Threshold

Flags fields with confidence below the threshold (default: 0.5).

```json
{"severity": "warning", "rule": "low_confidence",
 "message": "Field 'date' has low confidence: 0.3",
 "fields": ["date"]}
```

### Arithmetic Validation (Invoice-Specific)

For invoice schemas, ADX verifies that `subtotal + tax = total`:

```json
{"severity": "error", "rule": "arithmetic",
 "message": "subtotal (1000) + tax (100) != total (1200). Difference: 100",
 "fields": ["subtotal", "tax", "total"]}
```

## Severity Levels

| Severity | Meaning |
|---|---|
| `error` | Critical issue — extraction is likely wrong |
| `warning` | Potential issue — review recommended |
| `info` | Informational — no action needed |

## REST API

```bash
# Validate an extraction
curl -X POST http://localhost:8000/v1/files/{id}/validate \
  -H "Content-Type: application/json" \
  -d '{"extraction_id": "ext_abc123"}'
```

## CLI

```bash
adx validate <doc_id> --extraction <extraction_id>
```
