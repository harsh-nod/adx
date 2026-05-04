---
title: Financial Model
---

# Financial Model Analysis

This example inspects an Excel financial model: navigating sheets, reading ranges, tracing formulas, and extracting key metrics.

## Upload

```python
from adx import ADX

dn = ADX()
doc_id = dn.upload("model.xlsx")
```

## List Sheets

```python
sheets = dn.list_sheets(doc_id)
for s in sheets["sheets"]:
    vis = "hidden" if s["hidden"] else "visible"
    print(f"  {s['name']}: {s['rows']}x{s['cols']} ({vis})")
```

```
  Summary: 25x8 (visible)
  Assumptions: 15x4 (visible)
  Details: 50x12 (hidden)
```

## Read Key Ranges

```python
# Read the summary section
data = dn.read_range(doc_id, sheet="Summary", range="A1:D10")
for cell in data["cells"]:
    formula = f" = {cell['formula']}" if cell.get("formula") else ""
    print(f"  {cell['address']}: {cell['value']}{formula}")
```

```
  A1: Financial Summary
  A3: Revenue    B3: 1500000 = =Assumptions!B2*Assumptions!B3
  A4: Expenses   B4: 900000  = =SUM(Details!B2:B20)
  A5: Net Income B5: 600000  = =B3-B4
```

## Trace Formulas

```python
info = dn.inspect_formula(doc_id, sheet="Summary", cell="B3")
print(f"Formula: {info['formula']}")
print(f"Value: {info['computed_value']}")
print(f"References: {info['references']}")
print(f"Cross-sheet: {info['cross_sheet_refs']}")
```

```
Formula: =Assumptions!B2*Assumptions!B3
Value: 1500000
References: ['Assumptions!B2', 'Assumptions!B3']
Cross-sheet: ['Assumptions']
```

## Read Assumptions

```python
assumptions = dn.read_range(doc_id, sheet="Assumptions", range="A1:B10")
for cell in assumptions["cells"]:
    print(f"  {cell['address']}: {cell['value']}")
```

## Find Specific Values

```python
results = dn.find_cells(doc_id, query="Growth")
for match in results["matches"]:
    print(f"  {match['sheet']}!{match['address']}: {match['value']}")
```

## Extract Key Metrics

```python
extraction = dn.extract(doc_id, schema="financial_model")
for field in extraction["fields"]:
    print(f"{field['name']}: {field['value']}")
    citation = field["citation"]
    print(f"  Source: {citation['sheet']}!{citation['cell']}")
```

## Validate

```python
result = dn.validate(doc_id, extraction["id"])
for check in result["checks"]:
    print(f"[{check['severity']}] {check['message']}")
```
