---
title: Document Model
---

# Document Model

ADX's canonical document model is a parser-agnostic representation called `DocumentGraph`. Every supported file format is normalized into this model.

## Schema Version

Current schema version: `0.1.0`

## Core Types

### DocumentGraph

The root container. One per uploaded file.

| Field | Type | Description |
|---|---|---|
| `schema_version` | `str` | Model schema version |
| `document` | `Document` | File metadata |
| `pages` | `Page[]` | Pages (PDF) |
| `workbook` | `Workbook` | Workbook (Excel/CSV) |
| `sections` | `Section[]` | Document sections |
| `citations` | `Citation[]` | All citations |
| `extractions` | `Extraction[]` | Extraction results |
| `confidence` | `ConfidenceSummary` | Overall confidence |

### Document

File-level metadata.

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique document ID |
| `file_name` | `str` | Original filename |
| `file_type` | `FileType` | `pdf`, `xlsx`, `csv` |
| `file_size` | `int` | Size in bytes |
| `document_type` | `DocumentType` | Detected type |
| `page_count` | `int` | Number of pages |
| `status` | `ProcessingStatus` | `pending`, `processing`, `ready`, `error` |

### Page

A single PDF page.

| Field | Type | Description |
|---|---|---|
| `page_number` | `int` | 1-indexed |
| `width` | `float` | Page width in points |
| `height` | `float` | Page height in points |
| `text_blocks` | `TextBlock[]` | Text on this page |
| `tables` | `Table[]` | Tables on this page |

### TextBlock

A block of text with position and classification.

| Field | Type | Description |
|---|---|---|
| `text` | `str` | The text content |
| `type` | `TextBlockType` | `heading`, `paragraph`, `header`, `footer` |
| `bbox` | `BoundingBox` | Position on page |
| `font_size` | `float` | Font size |
| `page` | `int` | Page number |

### Table

A table with rows and cells.

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique table ID |
| `page` | `int` | Page number |
| `row_count` | `int` | Number of rows |
| `col_count` | `int` | Number of columns |
| `cells` | `TableCell[]` | All cells |
| `has_header` | `bool` | Has header row |
| `bbox` | `BoundingBox` | Position on page |

### Workbook

A spreadsheet workbook.

| Field | Type | Description |
|---|---|---|
| `sheets` | `Sheet[]` | All sheets |

### Sheet

A single spreadsheet sheet.

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Sheet name |
| `index` | `int` | Sheet index |
| `row_count` | `int` | Number of rows |
| `col_count` | `int` | Number of columns |
| `cells` | `SpreadsheetCell[]` | All cells |
| `formulas` | `Formula[]` | All formulas |
| `hidden` | `bool` | Is sheet hidden |
| `named_ranges` | `dict` | Named range definitions |

### Citation

Provenance link back to source.

| Field | Type | Description |
|---|---|---|
| `type` | `CitationType` | `page`, `table`, `cell`, `range`, `formula` |
| `page` | `int` | Page number (PDF) |
| `bbox` | `BoundingBox` | Bounding box (PDF) |
| `sheet` | `str` | Sheet name (Excel) |
| `cell` | `str` | Cell address (Excel) |
| `range` | `str` | Cell range (Excel) |
| `text` | `str` | Source text snippet |

## Enums

### FileType
`pdf`, `xlsx`, `csv`

### DocumentType
`invoice`, `contract`, `financial_model`, `report`, `spreadsheet`, `general`

### ProcessingStatus
`pending`, `processing`, `ready`, `error`

### TextBlockType
`heading`, `paragraph`, `header`, `footer`

### CitationType
`page`, `table`, `cell`, `range`, `formula`

### ValidationSeverity
`error`, `warning`, `info`
