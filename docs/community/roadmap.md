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
- [x] **Legacy Excel (.xls) parsing** — xlrd adapter (Alpha)
- [x] **CSV parsing** — stdlib adapter with dialect sniffing (Alpha)
- [x] **DOCX parsing** — python-docx adapter with headings, tables, images, metadata (Alpha)
- [x] **PPTX parsing** — python-pptx adapter with slides, text, tables (Alpha)
- [x] **RTF parsing** — striprtf adapter with text extraction (Alpha)
- [x] **9 agent tools** — profile, structure, search, get_page, get_table, list_sheets, read_range, find_cells, inspect_formula (Alpha)
- [x] **Schema-driven extraction** — built-in schemas for invoice, contract, financial_model, table, register_spec, data_table (Alpha)
- [x] **Custom schemas** — register custom extraction schemas or pass JSON Schema dicts (Alpha)
- [x] **Validation engine** — required fields, types, arithmetic, citations, confidence (Alpha)
- [x] **Citation provenance** — every value traces to source page/cell/bbox with byte ranges (Alpha)
- [x] **Chunking API** — fixed-size and section-aware chunking for RAG pipelines (Alpha)
- [x] **Batch directory processing** — upload and process all files in a directory (Alpha)
- [x] **Corpus search** — search across all uploaded documents (Alpha)
- [x] **Markdown export** — render DocumentGraph as markdown (Alpha)
- [x] **REST API** — full FastAPI endpoint coverage with auth and rate limiting (Alpha)
- [x] **Python SDK** — synchronous ADX client (Alpha)
- [x] **Async Python SDK** — AsyncADX client with thread pool dispatch (Alpha)
- [x] **MCP server** — Model Context Protocol server with 10 tools (Alpha)
- [x] **CLI** — upload, profile, extract, validate, export, serve (Alpha)
- [x] **File-based storage** — JSON serialization of graphs and extractions (Alpha)

## Up Next

- [ ] LLM-powered extraction (optional enhancement)
- [ ] HTML parser adapter
- [ ] Stable API guarantees (v1.0)

## Not Yet Done

- No stable API guarantees — field names and response shapes may change before v1.0
- No LLM integration — extraction is heuristic-based for now
- No OCR — scanned PDFs require pre-processing
- No database storage — file-based only in MVP
