---
title: Contributing
---

# Contributing

Contributions are welcome. Here are areas where help is most useful:

- **Parser adapters** — add support for new formats (DOCX, HTML, etc.)
- **Extraction schemas** — add built-in schemas for new document types
- **Validation rules** — add domain-specific validation checks
- **MCP server** — implement the MCP tool interface
- **Documentation** — improve guides and examples
- **Test coverage** — expand unit and integration tests

## Workflow

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-change`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Make your changes — keep commits focused
5. Run tests: `pytest`
6. Open a PR with a clear description

## Code Style

- Python 3.11+
- Type hints on all public functions
- Pydantic v2 models for data structures
- Tests in `tests/` mirroring `src/` structure

## Architecture

```
src/docunav/
  models/       ← Pydantic document model
  parsers/      ← Parser adapters (PyMuPDF, openpyxl, csv)
  tools/        ← Agent inspection tools
  extraction/   ← Schema-driven extraction and validation
  storage/      ← File and graph storage
  api/          ← FastAPI REST endpoints
  cli.py        ← Click CLI
  client.py     ← Python SDK entry point
```

New parser adapters should implement the `ParserAdapter` abstract class in `parsers/base.py` and register in `parsers/registry.py`.
