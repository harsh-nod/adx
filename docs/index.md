---
title: ADX Overview
---

<div class="hero-intro">
  <h1>Agentic Data Layer</h1>
  <p class="hero-tagline">
    Profile. Inspect. Extract. Validate. Cite.<br>ADX gives your AI agents structured document tools.
  </p>
  <p class="hero-subtitle"><em>Documents are not text blobs. Give your agents document tools.</em></p>
  <div class="hero-actions">
    <a class="action primary" href="quickstart/">Get Started</a>
    <a class="action" href="guides/agent-tools">Agent Tools</a>
    <a class="action" href="https://github.com/harsh-nod/adx">View on GitHub</a>
  </div>
</div>

## How It Works

<div class="pipeline">
  <div class="pipeline-node">profile</div>
  <div class="pipeline-arrow"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="24" y2="6"/><polygon points="24,2 32,6 24,10"/></svg></div>
  <div class="pipeline-node">inspect</div>
  <div class="pipeline-arrow"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="24" y2="6"/><polygon points="24,2 32,6 24,10"/></svg></div>
  <div class="pipeline-node">extract</div>
  <div class="pipeline-arrow"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="24" y2="6"/><polygon points="24,2 32,6 24,10"/></svg></div>
  <div class="pipeline-node">validate</div>
  <div class="pipeline-arrow"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="24" y2="6"/><polygon points="24,2 32,6 24,10"/></svg></div>
  <div class="pipeline-node">cite</div>
</div>

Upload any document. ADX wraps best-in-class parsers and exposes a canonical, citeable, inspectable document model to your agents.

<div class="arch-diagram">
<svg viewBox="0 0 680 180" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="var(--vp-c-brand-1)"/>
    </marker>
    <marker id="arrowhead-dim" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="var(--vp-c-text-2)"/>
    </marker>
  </defs>
  <!-- Agent box -->
  <rect class="arch-box" x="10" y="40" width="140" height="90"/>
  <text class="arch-label" x="80" y="75" text-anchor="middle">AI Agent</text>
  <text class="arch-sublabel" x="80" y="95" text-anchor="middle">Claude, GPT,</text>
  <text class="arch-sublabel" x="80" y="110" text-anchor="middle">or any MCP client</text>
  <!-- Arrows -->
  <line class="arch-arrow" x1="150" y1="72" x2="230" y2="72"/>
  <line class="arch-arrow-back" x1="230" y1="98" x2="150" y2="98"/>
  <!-- ADX box -->
  <g class="proxy-group">
    <rect class="arch-box-accent" x="230" y="20" width="220" height="150"/>
    <text class="arch-label" x="340" y="48" text-anchor="middle">ADX</text>
    <rect class="arch-box" x="250" y="58" width="180" height="100"/>
    <text class="arch-sublabel" x="268" y="78">profile_document</text>
    <text class="arch-sublabel" x="268" y="94">search_document</text>
    <text class="arch-sublabel" x="268" y="110">extract (schema)</text>
    <text class="arch-sublabel" x="268" y="126">validate + cite</text>
    <text class="arch-sublabel" x="268" y="146">read_range, formulas</text>
  </g>
  <!-- Arrows -->
  <line class="arch-arrow" x1="450" y1="72" x2="530" y2="72"/>
  <line class="arch-arrow-back" x1="530" y1="98" x2="450" y2="98"/>
  <!-- Parsers box -->
  <rect class="arch-box" x="530" y="40" width="140" height="90"/>
  <text class="arch-label" x="600" y="75" text-anchor="middle">Parsers</text>
  <text class="arch-sublabel" x="600" y="95" text-anchor="middle">PyMuPDF, openpyxl</text>
  <text class="arch-sublabel" x="600" y="110" text-anchor="middle">csv, custom</text>
</svg>
</div>

<div class="demo-grid">
<div class="demo-panel demo-danger">
<h4>Without ADX</h4>

```
Agent: reads invoice.pdf as raw text
Agent: tries regex on flattened string
Agent: misses table spanning pages 2-3
Agent: extracts wrong total
Agent: no way to verify the answer
```

Raw text dumps lose structure, tables, and provenance. The agent hallucinates fields it cannot cite.
</div>
<div class="demo-panel demo-safe">
<h4>With ADX</h4>

```python
from adx import ADX
dn = ADX()
doc_id = dn.upload("invoice.pdf")
profile = dn.profile(doc_id)
extraction = dn.extract(doc_id, schema="invoice")
result = dn.validate(doc_id, extraction.id)
```

```json
{"field": "total", "value": 4250.00,
 "confidence": 0.95,
 "citation": {"page": 3, "bbox": [72, 680, 540, 700]}}
```

Every field is extracted with a citation. Every value is validated.
</div>
</div>

## What ADX Does

ADX is **not** a parser. It is an orchestration layer that:

1. **Wraps** best-in-class parsers (PyMuPDF, openpyxl, csv) behind a uniform interface
2. **Builds** a canonical `DocumentGraph` from any supported file format
3. **Exposes** structured, read-only agent tools for inspection and search
4. **Extracts** fields using built-in schemas with field-level citations
5. **Validates** results with rule-based checks (types, arithmetic, citations)

## Quick Start

```bash
pip install adx

# Start the server
adx serve

# Upload and profile a document
curl -X POST http://localhost:8000/v1/files -F "file=@invoice.pdf"
curl http://localhost:8000/v1/files/{id}/profile
```

Or use the Python SDK directly:

```python
from adx import ADX

dn = ADX()
doc_id = dn.upload("invoice.pdf")
print(dn.profile(doc_id))
print(dn.structure(doc_id))
extraction = dn.extract(doc_id, schema="invoice")
print(dn.validate(doc_id, extraction.id))
```

## Agent Tools

Nine read-only, deterministic tools that return structured JSON:

<div class="landing-grid">
  <article class="card">
    <h3>profile_document</h3>
    <p>File metadata, page count, detected type, confidence scores, and recommended next tools.</p>
  </article>
  <article class="card">
    <h3>list_structure</h3>
    <p>Headings, sections, table locations, and page-level outline for navigation.</p>
  </article>
  <article class="card">
    <h3>search_document</h3>
    <p>Full-text search with page/cell locations and surrounding context snippets.</p>
  </article>
  <article class="card">
    <h3>get_page / get_table</h3>
    <p>Retrieve a specific page's text blocks or a table's rows with bounding boxes.</p>
  </article>
  <article class="card">
    <h3>list_sheets / read_range</h3>
    <p>Navigate spreadsheet sheets and read cell ranges with formulas and computed values.</p>
  </article>
  <article class="card">
    <h3>find_cells / inspect_formula</h3>
    <p>Search cells by value or pattern. Trace formula dependencies and precedents.</p>
  </article>
  <article class="card">
    <h3>Schema Extraction</h3>
    <p>Built-in schemas for invoices, contracts, and financial models. Field-level citations included.</p>
  </article>
  <article class="card">
    <h3>Validation Engine</h3>
    <p>Rule-based checks: required fields, type coercion, arithmetic verification, citation provenance.</p>
  </article>
</div>

## Integrations

<div class="integrations">
  <div>
    <h3>Python SDK</h3>
    <p>Upload, inspect, extract, and validate documents with a single client object.</p>

```python
from adx import ADX

dn = ADX()
doc_id = dn.upload("report.pdf")
profile = dn.profile(doc_id)
tables = dn.structure(doc_id)["tables"]
data = dn.get_table(doc_id, tables[0]["id"])
```
  </div>
  <div>
    <h3>REST API</h3>
    <p>Full HTTP API for language-agnostic integration. Start with <code>adx serve</code>.</p>

```bash
# Upload
curl -X POST localhost:8000/v1/files -F "file=@model.xlsx"

# Extract with schema
curl -X POST localhost:8000/v1/files/{id}/extract \
  -H "Content-Type: application/json" \
  -d '{"schema": "financial_model"}'
```
  </div>
  <div>
    <h3>CLI</h3>
    <p>Command-line tools for scripting and CI pipelines.</p>

```bash
adx upload invoice.pdf
adx profile <id>
adx extract <id> --schema invoice
adx validate <id> --extraction <eid>
adx export <id> --format markdown
```
  </div>
</div>

## Supported Formats

| Format | Parser | Features |
|---|---|---|
| PDF | PyMuPDF | Text blocks, tables, bounding boxes, section detection |
| Excel (.xlsx) | openpyxl | Sheets, formulas, named ranges, hidden cells, merged cells |
| DOCX | python-docx | Paragraphs, headings, tables, images, metadata |
| RTF | striprtf | Text extraction with formatting stripped |
| CSV | stdlib csv | Dialect sniffing, encoding detection, header inference |

## Learn More

- [Quickstart](quickstart/) for a five-minute walkthrough.
- [Agent Tools](guides/agent-tools) for the full tool reference.
- [PDF Guide](guides/pdf-processing) for PDF-specific features.
- [Excel Guide](guides/excel-processing) for spreadsheet-specific features.
- [API Reference](reference/api) for every endpoint.
- [Examples](examples/) for real-world extraction workflows.
