---
title: Batch Operations
---

# Batch Operations

ADX supports uploading and processing entire directories of documents in a single call.

## Directory Upload

### Python SDK

```python
from adx import ADX

dn = ADX()
result = dn.upload_directory("./documents/", recursive=True)

print(f"Processed {result.successful}/{result.total_files} files")
if result.errors:
    for path, error in result.errors.items():
        print(f"  Failed: {path} — {error}")

# Access processed file IDs
for file_id in result.graphs:
    profile = dn.profile(file_id)
    print(profile["file_name"], profile["document_type"])
```

### Filter by Extension

```python
result = dn.upload_directory(
    "./documents/",
    recursive=True,
    extensions={".pdf", ".xlsx"},
)
```

### BatchResult

| Field | Type | Description |
|---|---|---|
| `total_files` | `int` | Total files found |
| `successful` | `int` | Successfully processed |
| `failed` | `int` | Failed to process |
| `graphs` | `list[str]` | File IDs of successful uploads |
| `errors` | `dict[str, str]` | File path to error message mapping |

## Async Batch Upload

For concurrent processing of multiple files:

```python
import asyncio
from adx import AsyncADX

async def main():
    dn = AsyncADX(max_workers=4)

    # Upload multiple files concurrently
    graphs = await dn.upload_many([
        "invoice_1.pdf",
        "invoice_2.pdf",
        "model.xlsx",
        "contract.docx",
    ])

    for graph in graphs:
        print(graph.document.id, graph.document.filename)

asyncio.run(main())
```

You can also upload a directory asynchronously:

```python
async def main():
    dn = AsyncADX()
    result = await dn.upload_directory("./documents/", recursive=True)
    print(f"Done: {result.successful} files")
```

## REST API

```bash
curl -X POST http://localhost:8000/v1/directories \
  -H "Content-Type: application/json" \
  -d '{"path": "./documents/", "recursive": true, "extensions": [".pdf", ".xlsx"]}'
```
