---
title: Roadmap
---

# Roadmap

## Maturity

| Level | Meaning |
|---|---|
| Stable | Tested, documented, API won't break |
| Alpha | Works, API may change |
| Experimental | Proof of concept |
| Planned | Not yet started |

## Implemented

- [x] **Canonical DocumentGraph model** — parser-agnostic document representation (Alpha)
- [x] **PDF parsing** — PyMuPDF adapter with text blocks, tables, bounding boxes (Alpha)
- [x] **Excel parsing** — openpyxl adapter with formulas, hidden content, named ranges (Alpha)
- [x] **CSV parsing** — stdlib adapter with dialect sniffing (Alpha)
- [x] **9 agent tools** — profile, structure, search, get_page, get_table, list_sheets, read_range, find_cells, inspect_formula (Alpha)
- [x] **Schema-driven extraction** — built-in schemas for invoice, contract, financial_model, table (Alpha)
- [x] **Validation engine** — required fields, types, arithmetic, citations, confidence (Alpha)
- [x] **Citation provenance** — every value traces to source page/cell/bbox (Alpha)
- [x] **REST API** — full FastAPI endpoint coverage (Alpha)
- [x] **Python SDK** — single-client interface for all operations (Alpha)
- [x] **CLI** — upload, profile, extract, validate, export, serve (Alpha)
- [x] **File-based storage** — JSON serialization of graphs and extractions (Alpha)

## Up Next

- [ ] MCP server implementation
- [ ] LLM-powered extraction (optional enhancement)
- [ ] DOCX parser adapter
- [ ] HTML parser adapter
- [ ] Stable API guarantees (v1.0)

## Not Yet Done

- No stable API guarantees — field names and response shapes may change before v1.0
- No MCP server — planned, tools are designed for it
- No LLM integration — extraction is heuristic-based for now
- No OCR — scanned PDFs require pre-processing
- No database storage — file-based only in MVP
