---
title: CLI Reference
---

# CLI Reference

```bash
pip install adx
```

## Commands

### adx upload

Upload a document.

```bash
adx upload invoice.pdf
adx upload model.xlsx
adx upload data.csv
```

### adx files

List uploaded documents.

```bash
adx files
```

### adx profile

Profile a document.

```bash
adx profile <doc_id>
```

### adx structure

Show document structure.

```bash
adx structure <doc_id>
```

### adx search

Search a document.

```bash
adx search <doc_id> --query "payment terms"
```

### adx sheets

List spreadsheet sheets.

```bash
adx sheets <doc_id>
```

### adx extract

Extract fields with a schema.

```bash
adx extract <doc_id> --schema invoice
adx extract <doc_id> --schema contract
adx extract <doc_id> --schema financial_model
```

### adx validate

Validate an extraction.

```bash
adx validate <doc_id> --extraction <extraction_id>
```

### adx export

Export document content.

```bash
adx export <doc_id> --format json
adx export <doc_id> --format markdown
adx export <doc_id> --format csv
```

### adx serve

Start the REST API server.

```bash
adx serve
adx serve --host 0.0.0.0 --port 9000
```

Default: `http://localhost:8000`
