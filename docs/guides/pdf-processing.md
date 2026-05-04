---
title: PDF Processing
---

# PDF Processing

ADX uses PyMuPDF (fitz) to parse PDFs into structured `DocumentGraph` objects. This guide covers PDF-specific features.

## What Gets Extracted

- **Text blocks** with bounding boxes and classification (heading, paragraph, header, footer)
- **Tables** with row/column structure and cell values
- **Sections** inferred from heading hierarchy and font sizes
- **Figures/images** detected with bounding boxes
- **Page-level metadata** — dimensions, text density

## Heading Detection

Text blocks are classified by font size relative to the page average:

- Font size > 1.5x average → heading
- Position in top 10% of page → header
- Position in bottom 10% of page → footer
- Everything else → paragraph

Headings drive section detection. Sections are nested by font size to build a document outline.

## Table Extraction

PyMuPDF's `find_tables()` extracts tabular data with cell boundaries. Tables are converted to structured `Table` objects with:

- Row and column counts
- Header row detection
- Cell-level values
- Bounding boxes for citation
- Markdown rendering via `table.to_markdown()`

## Scanned PDF Detection

ADX warns when a page appears to be scanned (image-based) rather than text-based. Pages with fewer than 20 characters of extracted text trigger a `possibly_scanned` warning.

For scanned PDFs, consider using an OCR pre-processing step before uploading to ADX.

## Citations

Every text block and table gets a `Citation` with:
- `page` — 1-indexed page number
- `bbox` — `[x0, y0, x1, y1]` coordinates in PDF points
- `text` — the source text snippet

Citations flow through to extractions, so every extracted field traces back to its source location in the PDF.

## Example

```python
from adx import ADX

dn = ADX()
doc_id = dn.upload("contract.pdf")

# Get document structure
structure = dn.structure(doc_id)
for section in structure["sections"]:
    print(f"Section: {section['title']} (pages {section['start_page']}-{section['end_page']})")

# Read a specific page
page = dn.get_page(doc_id, page_number=1)
for block in page["text_blocks"]:
    print(f"[{block['type']}] {block['text'][:80]}...")

# Get a table
tables = structure["tables"]
if tables:
    table = dn.get_table(doc_id, tables[0]["id"])
    print(table["markdown"])
```

## Limitations

- Scanned PDFs require OCR pre-processing (not built in)
- Complex multi-column layouts may produce fragmented text blocks
- Form fields (AcroForm) are not yet extracted
- Annotations and comments are not yet extracted
