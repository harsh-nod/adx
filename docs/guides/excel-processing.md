---
title: Excel Processing
---

# Excel Processing

ADX uses openpyxl to parse Excel files (.xlsx) into structured `DocumentGraph` objects. This guide covers spreadsheet-specific features.

## What Gets Extracted

- **Sheets** with dimensions, visibility, and named ranges
- **Cells** with values, types, and formatting info
- **Formulas** with computed values and dependency tracking
- **Hidden sheets, rows, and columns** — flagged but still accessible
- **Merged cells** — detected and reported
- **Comments** — extracted as metadata
- **Named ranges** — mapped to their cell references
- **External links** — detected and flagged

## Dual-Mode Loading

ADX loads each workbook twice:
1. **Formula mode** — preserves formula text (e.g., `=SUM(A1:A10)`)
2. **Data-only mode** — reads calculated values (e.g., `42.5`)

This means agents can see both what a cell *computes* and what it *says*.

## Formula Inspection

The `inspect_formula` tool traces formula dependencies:

```python
info = dn.inspect_formula(doc_id, sheet="Summary", cell="B10")
```

Returns:
- The formula text
- The computed value
- All referenced cells and ranges
- Cross-sheet references
- External workbook references

## Hidden Content Detection

ADX tracks hidden elements:
- Hidden sheets (visible in `list_sheets` with `hidden: true`)
- Hidden rows and columns (flagged in `read_range` results)
- Cells in hidden rows/columns are accessible but marked

## Named Ranges

Named ranges are extracted and available through `list_sheets`:

```python
sheets = dn.list_sheets(doc_id)
for sheet in sheets["sheets"]:
    for nr in sheet.get("named_ranges", []):
        print(f"  {nr['name']}: {nr['range']}")
```

## Cell Search

Find cells by value across sheets:

```python
results = dn.find_cells(doc_id, query="Revenue")
for match in results["matches"]:
    print(f"  {match['sheet']}!{match['address']}: {match['value']}")
```

## Range Reading

Read a rectangular range of cells:

```python
data = dn.read_range(doc_id, sheet="Assumptions", range="A1:C20")
for cell in data["cells"]:
    print(f"  {cell['address']}: {cell['value']} (formula: {cell.get('formula', 'N/A')})")
```

## Example

```python
from adx import ADX

dn = ADX()
doc_id = dn.upload("financial_model.xlsx")

# List all sheets
sheets = dn.list_sheets(doc_id)
for s in sheets["sheets"]:
    visibility = "hidden" if s["hidden"] else "visible"
    print(f"  {s['name']}: {s['rows']}x{s['cols']} ({visibility})")

# Read a range
data = dn.read_range(doc_id, sheet="Summary", range="A1:D10")

# Inspect a formula
formula = dn.inspect_formula(doc_id, sheet="Summary", cell="D10")
print(f"Formula: {formula['formula']}")
print(f"Value: {formula['computed_value']}")
print(f"References: {formula['references']}")

# Extract financial model fields
extraction = dn.extract(doc_id, schema="financial_model")
```

## Limitations

- Only `.xlsx` format is supported (not `.xls` or `.xlsb`)
- Pivot tables are not parsed (read as static values)
- Charts are not extracted
- Macros (VBA) are not executed or analyzed
- Conditional formatting rules are not extracted
