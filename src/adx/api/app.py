"""FastAPI application — REST API for ADX."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from adx.client import ADX

app = FastAPI(
    title="ADX: Agentic Data Layer",
    description="Agent-native document intelligence layer. Structured, citeable, inspectable document state for AI agents.",
    version="0.1.0",
)

_client: ADX | None = None


def get_client() -> ADX:
    global _client
    if _client is None:
        _client = ADX()
    return _client


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class ProcessRequest(BaseModel):
    file_id: str | None = None


class SearchRequest(BaseModel):
    query: str
    max_results: int = 20


class RangeRequest(BaseModel):
    sheet_name: str
    range: str


class FindCellsRequest(BaseModel):
    query: str
    sheet_name: str | None = None
    max_results: int = 20


class FormulaRequest(BaseModel):
    sheet_name: str
    cell_address: str


class ExtractRequest(BaseModel):
    schema: str | dict[str, Any] | None = None
    instructions: str | None = None


class ExportRequest(BaseModel):
    format: str = "json"


# ---------------------------------------------------------------------------
# File endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/files", tags=["files"])
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    """Upload and process a file."""
    client = get_client()
    data = await file.read()
    filename = file.filename or "unknown"

    try:
        graph = client.upload_bytes(data, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(
        status_code=201,
        content={
            "file_id": graph.document.id,
            "filename": graph.document.filename,
            "file_type": graph.document.file_type.value,
            "page_count": graph.document.page_count,
            "sheet_count": graph.document.sheet_count,
            "status": graph.document.processing_status.value,
        },
    )


@app.get("/v1/files/{file_id}", tags=["files"])
async def get_file(file_id: str) -> JSONResponse:
    """Get file metadata."""
    client = get_client()
    graph = client.get_graph(file_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="File not found.")
    return JSONResponse(content={
        "file_id": graph.document.id,
        "filename": graph.document.filename,
        "file_type": graph.document.file_type.value,
        "mime_type": graph.document.mime_type,
        "checksum": graph.document.checksum,
        "page_count": graph.document.page_count,
        "sheet_count": graph.document.sheet_count,
        "status": graph.document.processing_status.value,
        "created_at": graph.document.created_at.isoformat(),
    })


@app.get("/v1/files", tags=["files"])
async def list_files() -> JSONResponse:
    """List all processed files."""
    client = get_client()
    ids = client.list_files()
    files = []
    for fid in ids:
        graph = client.get_graph(fid)
        if graph:
            files.append({
                "file_id": graph.document.id,
                "filename": graph.document.filename,
                "file_type": graph.document.file_type.value,
                "status": graph.document.processing_status.value,
            })
    return JSONResponse(content={"files": files})


class DirectoryRequest(BaseModel):
    path: str
    recursive: bool = True
    extensions: list[str] | None = None


class CorpusSearchRequest(BaseModel):
    query: str
    file_ids: list[str] | None = None
    max_results: int = 20


@app.post("/v1/directories", tags=["files"])
async def upload_directory(body: DirectoryRequest) -> JSONResponse:
    """Upload all supported files in a directory."""
    client = get_client()
    try:
        exts = set(body.extensions) if body.extensions else None
        result = client.upload_directory(body.path, recursive=body.recursive, extensions=exts)
        return JSONResponse(
            status_code=201,
            content={
                "total_files": result.total_files,
                "successful": result.successful,
                "failed": result.failed,
                "graphs": result.graphs,
                "errors": result.errors,
            },
        )
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/search", tags=["search"])
async def search_corpus(body: CorpusSearchRequest) -> JSONResponse:
    """Search across all stored document graphs."""
    client = get_client()
    hits = client.search_corpus(body.query, body.file_ids, body.max_results)
    return JSONResponse(content={"query": body.query, "results": hits, "total": len(hits)})


@app.get("/v1/files/{file_id}/markdown", tags=["files"])
async def get_markdown(file_id: str) -> JSONResponse:
    """Export document as markdown."""
    client = get_client()
    try:
        md = client.to_markdown(file_id)
        return JSONResponse(content={"file_id": file_id, "markdown": md})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Inspection endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/files/{file_id}/profile", tags=["inspection"])
async def profile_document(file_id: str) -> JSONResponse:
    """Profile a document."""
    client = get_client()
    try:
        return JSONResponse(content=client.profile(file_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/structure", tags=["inspection"])
async def get_structure(file_id: str) -> JSONResponse:
    """Get document structure."""
    client = get_client()
    try:
        return JSONResponse(content=client.structure(file_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/files/{file_id}/search", tags=["inspection"])
async def search_document(file_id: str, body: SearchRequest) -> JSONResponse:
    """Search document content."""
    client = get_client()
    try:
        return JSONResponse(content=client.search(file_id, body.query, body.max_results))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/pages/{page_number}", tags=["inspection"])
async def get_page(file_id: str, page_number: int) -> JSONResponse:
    """Inspect a page."""
    client = get_client()
    try:
        result = client.get_page(file_id, page_number)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/tables", tags=["inspection"])
async def list_tables(file_id: str) -> JSONResponse:
    """List all tables in a document."""
    client = get_client()
    try:
        structure = client.structure(file_id)
        return JSONResponse(content={"tables": structure.get("tables", [])})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/tables/{table_id}", tags=["inspection"])
async def get_table(file_id: str, table_id: str) -> JSONResponse:
    """Inspect a table."""
    client = get_client()
    try:
        result = client.get_table(file_id, table_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/sheets", tags=["inspection"])
async def list_sheets(file_id: str) -> JSONResponse:
    """List workbook sheets."""
    client = get_client()
    try:
        result = client.list_sheets(file_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/files/{file_id}/ranges/read", tags=["inspection"])
async def read_range(file_id: str, body: RangeRequest) -> JSONResponse:
    """Read a spreadsheet range."""
    client = get_client()
    try:
        result = client.read_range(file_id, body.sheet_name, body.range)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/files/{file_id}/cells/find", tags=["inspection"])
async def find_cells(file_id: str, body: FindCellsRequest) -> JSONResponse:
    """Find spreadsheet cells."""
    client = get_client()
    try:
        return JSONResponse(content=client.find_cells(file_id, body.query, body.sheet_name))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/files/{file_id}/formulas/inspect", tags=["inspection"])
async def inspect_formula(file_id: str, body: FormulaRequest) -> JSONResponse:
    """Inspect a formula."""
    client = get_client()
    try:
        result = client.inspect_formula(file_id, body.sheet_name, body.cell_address)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Extraction endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/files/{file_id}/extract", tags=["extraction"])
async def extract(file_id: str, body: ExtractRequest) -> JSONResponse:
    """Run schema-based extraction."""
    client = get_client()
    try:
        extraction = client.extract(file_id, body.schema, body.instructions)
        return JSONResponse(content={
            "extraction_id": extraction.id,
            "document_id": extraction.document_id,
            "schema": extraction.schema_name,
            "status": extraction.status,
            "confidence": extraction.confidence,
            "output": extraction.output,
            "fields": [
                {
                    "field": f.field_path,
                    "value": f.value,
                    "confidence": f.confidence,
                    "citations": [c.model_dump() for c in f.citations],
                    "warnings": f.warnings,
                }
                for f in extraction.fields
            ],
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/extractions/{extraction_id}", tags=["extraction"])
async def get_extraction(extraction_id: str) -> JSONResponse:
    """Get extraction result."""
    client = get_client()
    extraction = client.get_extraction(extraction_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extraction not found.")
    return JSONResponse(content={
        "extraction_id": extraction.id,
        "document_id": extraction.document_id,
        "schema": extraction.schema_name,
        "status": extraction.status,
        "confidence": extraction.confidence,
        "output": extraction.output,
        "fields": [
            {
                "field": f.field_path,
                "value": f.value,
                "confidence": f.confidence,
                "citations": [c.model_dump() for c in f.citations],
                "warnings": f.warnings,
            }
            for f in extraction.fields
        ],
    })


@app.post("/v1/extractions/{extraction_id}/validate", tags=["extraction"])
async def validate_extraction(extraction_id: str) -> JSONResponse:
    """Validate an extraction."""
    client = get_client()
    try:
        results = client.validate(extraction_id)
        return JSONResponse(content={
            "extraction_id": extraction_id,
            "validation_results": [
                {
                    "severity": r.severity.value,
                    "rule": r.rule_name,
                    "message": r.message,
                    "affected_fields": r.affected_fields,
                    "status": r.status,
                }
                for r in results
            ],
            "passed": all(r.severity.value != "error" for r in results),
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/extractions/{extraction_id}/citations", tags=["extraction"])
async def get_citations(extraction_id: str) -> JSONResponse:
    """Get source citations for an extraction."""
    client = get_client()
    extraction = client.get_extraction(extraction_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extraction not found.")
    return JSONResponse(content={
        "extraction_id": extraction_id,
        "citations": [
            {
                "field": f.field_path,
                "citations": [c.model_dump() for c in f.citations],
            }
            for f in extraction.fields
        ],
    })


@app.post("/v1/extractions/{extraction_id}/export", tags=["extraction"])
async def export_extraction(extraction_id: str, body: ExportRequest) -> JSONResponse:
    """Export extraction results."""
    client = get_client()
    try:
        result = client.export(extraction_id, body.format)
        return JSONResponse(content={"format": body.format, "data": result})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
async def health() -> JSONResponse:
    return JSONResponse(content={"status": "ok", "version": "0.1.0"})
