---
title: CLI Reference
---

# CLI Reference

```bash
pip install docunav
```

## Commands

### docunav upload

Upload a document.

```bash
docunav upload invoice.pdf
docunav upload model.xlsx
docunav upload data.csv
```

### docunav files

List uploaded documents.

```bash
docunav files
```

### docunav profile

Profile a document.

```bash
docunav profile <doc_id>
```

### docunav structure

Show document structure.

```bash
docunav structure <doc_id>
```

### docunav search

Search a document.

```bash
docunav search <doc_id> --query "payment terms"
```

### docunav sheets

List spreadsheet sheets.

```bash
docunav sheets <doc_id>
```

### docunav extract

Extract fields with a schema.

```bash
docunav extract <doc_id> --schema invoice
docunav extract <doc_id> --schema contract
docunav extract <doc_id> --schema financial_model
```

### docunav validate

Validate an extraction.

```bash
docunav validate <doc_id> --extraction <extraction_id>
```

### docunav export

Export document content.

```bash
docunav export <doc_id> --format json
docunav export <doc_id> --format markdown
docunav export <doc_id> --format csv
```

### docunav serve

Start the REST API server.

```bash
docunav serve
docunav serve --host 0.0.0.0 --port 9000
```

Default: `http://localhost:8000`
