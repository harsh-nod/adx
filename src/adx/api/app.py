"""FastAPI application — REST API for ADX."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from adx.client import ADX

app = FastAPI(
    title="ADX: Agentic Data Layer",
    description="Agent-native document intelligence layer. Structured, citeable, inspectable document state for AI agents.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Client dependency injection (replaces global mutable singleton)
# ---------------------------------------------------------------------------

_client_instance: ADX | None = None


def configure_client(storage_dir: str | Path | None = None, api_key: str | None = None) -> None:
    """Configure the ADX client for the API. Call at app startup."""
    global _client_instance
    _client_instance = ADX(storage_dir=storage_dir, api_key=api_key)


def get_client() -> ADX:
    """FastAPI dependency that provides the ADX client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = ADX()
    return _client_instance


# ---------------------------------------------------------------------------
# Optional API key authentication
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Depends(_api_key_header)) -> None:
    """Enforce API key auth when ADX_API_KEY env var is set."""
    expected = os.environ.get("ADX_API_KEY")
    if expected is None:
        return  # Auth not configured — allow all
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


# ---------------------------------------------------------------------------
# Simple in-memory rate limiter
# ---------------------------------------------------------------------------

_rate_limit_window: float = 60.0  # seconds
_rate_limit_max: int = int(os.environ.get("ADX_RATE_LIMIT", "120"))  # requests per window
_request_counts: dict[str, list[float]] = defaultdict(list)


async def rate_limit(request: Request) -> None:
    """Simple per-IP rate limiter."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    timestamps = _request_counts[client_ip]

    # Prune old timestamps
    _request_counts[client_ip] = [t for t in timestamps if now - t < _rate_limit_window]
    timestamps = _request_counts[client_ip]

    if len(timestamps) >= _rate_limit_max:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    timestamps.append(now)


# Apply auth and rate limiting to all endpoints
app_deps = [Depends(verify_api_key), Depends(rate_limit)]


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

@app.post("/v1/files", tags=["files"], dependencies=app_deps)
async def upload_file(
    file: UploadFile = File(...),
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Upload and process a file."""
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


@app.get("/v1/files/{file_id}", tags=["files"], dependencies=app_deps)
async def get_file(file_id: str, client: ADX = Depends(get_client)) -> JSONResponse:
    """Get file metadata."""
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


@app.get("/v1/files", tags=["files"], dependencies=app_deps)
async def list_files(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """List processed files with pagination."""
    ids = client.list_files()
    total = len(ids)
    paginated_ids = ids[offset : offset + limit]
    files = []
    for fid in paginated_ids:
        graph = client.get_graph(fid)
        if graph:
            files.append({
                "file_id": graph.document.id,
                "filename": graph.document.filename,
                "file_type": graph.document.file_type.value,
                "status": graph.document.processing_status.value,
            })
    return JSONResponse(content={
        "files": files,
        "total": total,
        "limit": limit,
        "offset": offset,
    })


class DirectoryRequest(BaseModel):
    path: str
    recursive: bool = True
    extensions: list[str] | None = None


class CorpusSearchRequest(BaseModel):
    query: str
    file_ids: list[str] | None = None
    max_results: int = 20
    offset: int = 0


@app.post("/v1/directories", tags=["files"], dependencies=app_deps)
async def upload_directory(
    body: DirectoryRequest,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Upload all supported files in a directory."""
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


@app.post("/v1/search", tags=["search"], dependencies=app_deps)
async def search_corpus(
    body: CorpusSearchRequest,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Search across all stored document graphs."""
    hits = client.search_corpus(body.query, body.file_ids, body.max_results + body.offset)
    paginated = hits[body.offset : body.offset + body.max_results]
    return JSONResponse(content={
        "query": body.query,
        "results": paginated,
        "total": len(hits),
        "offset": body.offset,
    })


class ChunkRequest(BaseModel):
    strategy: str = "section_aware"
    max_chunk_size: int = 1000
    overlap: int = 200


@app.post("/v1/files/{file_id}/chunks", tags=["chunking"], dependencies=app_deps)
async def chunk_document(
    file_id: str,
    body: ChunkRequest,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Chunk a document for retrieval."""
    try:
        chunks = client.chunk(
            file_id,
            strategy=body.strategy,
            max_chunk_size=body.max_chunk_size,
            overlap=body.overlap,
        )
        return JSONResponse(content={
            "file_id": file_id,
            "chunk_count": len(chunks),
            "chunks": [
                {
                    "id": c.id,
                    "text": c.text,
                    "chunk_type": c.chunk_type,
                    "section_path": c.section_path,
                    "page_numbers": c.page_numbers,
                    "sheet_name": c.sheet_name,
                    "token_count": c.token_count,
                    "citations": [ci.model_dump() for ci in c.citations],
                }
                for c in chunks
            ],
        })
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/markdown", tags=["files"], dependencies=app_deps)
async def get_markdown(
    file_id: str,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Export document as markdown."""
    try:
        md = client.to_markdown(file_id)
        return JSONResponse(content={"file_id": file_id, "markdown": md})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Inspection endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/files/{file_id}/profile", tags=["inspection"], dependencies=app_deps)
async def profile_document(
    file_id: str,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Profile a document."""
    try:
        return JSONResponse(content=client.profile(file_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/structure", tags=["inspection"], dependencies=app_deps)
async def get_structure(
    file_id: str,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Get document structure."""
    try:
        return JSONResponse(content=client.structure(file_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/files/{file_id}/search", tags=["inspection"], dependencies=app_deps)
async def search_document(
    file_id: str,
    body: SearchRequest,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Search document content."""
    try:
        return JSONResponse(content=client.search(file_id, body.query, body.max_results))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/pages/{page_number}", tags=["inspection"], dependencies=app_deps)
async def get_page(
    file_id: str,
    page_number: int,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Inspect a page."""
    try:
        result = client.get_page(file_id, page_number)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/tables", tags=["inspection"], dependencies=app_deps)
async def list_tables(
    file_id: str,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """List all tables in a document."""
    try:
        structure = client.structure(file_id)
        return JSONResponse(content={"tables": structure.get("tables", [])})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/tables/{table_id}", tags=["inspection"], dependencies=app_deps)
async def get_table(
    file_id: str,
    table_id: str,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Inspect a table."""
    try:
        result = client.get_table(file_id, table_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/v1/files/{file_id}/sheets", tags=["inspection"], dependencies=app_deps)
async def list_sheets(
    file_id: str,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """List workbook sheets."""
    try:
        result = client.list_sheets(file_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/files/{file_id}/ranges/read", tags=["inspection"], dependencies=app_deps)
async def read_range(
    file_id: str,
    body: RangeRequest,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Read a spreadsheet range."""
    try:
        result = client.read_range(file_id, body.sheet_name, body.range)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/files/{file_id}/cells/find", tags=["inspection"], dependencies=app_deps)
async def find_cells(
    file_id: str,
    body: FindCellsRequest,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Find spreadsheet cells."""
    try:
        return JSONResponse(content=client.find_cells(file_id, body.query, body.sheet_name))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/files/{file_id}/formulas/inspect", tags=["inspection"], dependencies=app_deps)
async def inspect_formula(
    file_id: str,
    body: FormulaRequest,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Inspect a formula."""
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

@app.post("/v1/files/{file_id}/extract", tags=["extraction"], dependencies=app_deps)
async def extract(
    file_id: str,
    body: ExtractRequest,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Run schema-based extraction."""
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


@app.get("/v1/extractions/{extraction_id}", tags=["extraction"], dependencies=app_deps)
async def get_extraction(
    extraction_id: str,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Get extraction result."""
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


@app.post("/v1/extractions/{extraction_id}/validate", tags=["extraction"], dependencies=app_deps)
async def validate_extraction(
    extraction_id: str,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Validate an extraction."""
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


@app.get("/v1/extractions/{extraction_id}/citations", tags=["extraction"], dependencies=app_deps)
async def get_citations(
    extraction_id: str,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Get source citations for an extraction."""
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


@app.post("/v1/extractions/{extraction_id}/export", tags=["extraction"], dependencies=app_deps)
async def export_extraction(
    extraction_id: str,
    body: ExportRequest,
    client: ADX = Depends(get_client),
) -> JSONResponse:
    """Export extraction results."""
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
