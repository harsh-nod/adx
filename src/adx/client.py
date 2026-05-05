"""ADX Python client — the main entry point for the SDK.

Usage:
    from adx import ADX

    client = ADX()
    file = client.upload("invoice.pdf")
    profile = client.profile(file.id)
    result = client.extract(file.id, schema="invoice")
    validation = client.validate(result.id)
    print(result.output)
    print(result.fields[0].citations)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from adx.extraction.extractor import Extractor
from adx.extraction.schemas import ExtractionSchema, SchemaRegistry
from adx.extraction.validator import Validator
from adx.models.document import (
    BatchResult,
    DocumentGraph,
    Extraction,
    ValidationResult,
)
from adx.parsers.graph_builder import GraphBuilder
from adx.parsers.registry import ParserRegistry
from adx.storage.store import DocumentStore
from adx.tools.inspector import DocumentInspector


class ADX:
    """High-level client for the ADX document intelligence layer."""

    def __init__(
        self,
        storage_dir: str | Path | None = None,
        api_key: str | None = None,
    ) -> None:
        self.store = DocumentStore(storage_dir)
        self.parser_registry = ParserRegistry()
        self.graph_builder = GraphBuilder()
        self.schema_registry = SchemaRegistry()
        self.extractor = Extractor(self.schema_registry)
        self.validator = Validator(self.schema_registry)
        self._api_key = api_key

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def upload(self, file_path: str | Path) -> DocumentGraph:
        """Upload, parse, and build a DocumentGraph from a file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_bytes = file_path.read_bytes()
        file_type = self.parser_registry.detect_file_type(file_path)

        # Parse
        result = self.parser_registry.parse(file_path, file_type)
        if not result.success:
            raise RuntimeError(f"Parsing failed: {'; '.join(result.errors)}")

        # Build graph
        graph = self.graph_builder.build(result, file_path, file_bytes)

        # Store
        self.store.store_file(file_path, graph.document.id)
        self.store.save_graph(graph)

        return graph

    def upload_bytes(self, data: bytes, filename: str) -> DocumentGraph:
        """Upload from bytes."""
        import tempfile

        with tempfile.NamedTemporaryFile(
            suffix=Path(filename).suffix, delete=False
        ) as tmp:
            tmp.write(data)
            tmp.flush()
            tmp_path = Path(tmp.name)

        try:
            file_type = self.parser_registry.detect_file_type(tmp_path)
            result = self.parser_registry.parse(tmp_path, file_type)
            if not result.success:
                raise RuntimeError(f"Parsing failed: {'; '.join(result.errors)}")

            graph = self.graph_builder.build(result, Path(filename), data)
            self.store.store_file_bytes(data, filename, graph.document.id)
            self.store.save_graph(graph)
            return graph
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError as cleanup_err:
                logger.warning("Failed to clean up temp file %s: %s", tmp_path, cleanup_err)

    def get_graph(self, file_id: str) -> DocumentGraph | None:
        """Load a previously processed DocumentGraph."""
        return self.store.load_graph(file_id)

    def list_files(self) -> list[str]:
        """List all processed file IDs."""
        return self.store.list_graphs()

    def to_markdown(self, file_id: str) -> str:
        """Render a document graph as markdown."""
        graph = self.store.load_graph(file_id)
        if graph is None:
            raise ValueError(f"File {file_id} not found. Upload and process it first.")
        return graph.to_markdown()

    def upload_directory(
        self,
        path: str | Path,
        recursive: bool = True,
        extensions: set[str] | None = None,
    ) -> BatchResult:
        """Upload all supported files in a directory."""
        from adx.parsers.registry import EXTENSION_MAP

        dir_path = Path(path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        supported_exts = extensions or set(EXTENSION_MAP.keys())
        files = dir_path.rglob("*") if recursive else dir_path.glob("*")
        file_list = sorted(
            f for f in files if f.is_file() and f.suffix.lower() in supported_exts
        )

        result = BatchResult(total_files=len(file_list))

        for file_path in file_list:
            try:
                graph = self.upload(file_path)
                result.graphs.append(graph.document.id)
                result.successful += 1
            except Exception as e:
                result.errors[str(file_path)] = str(e)
                result.failed += 1

        return result

    # ------------------------------------------------------------------
    # Corpus search
    # ------------------------------------------------------------------

    def search_corpus(
        self,
        query: str,
        file_ids: list[str] | None = None,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Search across all stored document graphs."""
        ids = file_ids or self.store.list_graphs()
        all_hits: list[dict[str, Any]] = []

        query_lower = query.lower()
        query_tokens = [w for w in query_lower.split() if len(w) >= 2]

        for fid in ids:
            graph = self.store.load_graph(fid)
            if graph is None:
                continue

            # Text search
            for page in graph.pages:
                for block in page.text_blocks:
                    text_lower = block.text.lower()
                    score = sum(text_lower.count(t) for t in query_tokens)
                    if score > 0:
                        all_hits.append({
                            "file_id": fid,
                            "filename": graph.document.filename,
                            "text_snippet": block.text[:200],
                            "page_number": page.page_number,
                            "sheet_name": None,
                            "score": score,
                            "citation": f"page {page.page_number}",
                        })

            # Cell search
            if graph.workbook:
                for sheet in graph.workbook.sheets:
                    for table in sheet.tables:
                        for cell in table.cells:
                            val_lower = str(cell.value).lower()
                            score = sum(val_lower.count(t) for t in query_tokens)
                            if score > 0:
                                addr = cell.source_cell_ref or f"R{cell.row_index}C{cell.column_index}"
                                all_hits.append({
                                    "file_id": fid,
                                    "filename": graph.document.filename,
                                    "text_snippet": str(cell.value)[:200],
                                    "page_number": None,
                                    "sheet_name": sheet.name,
                                    "score": score,
                                    "citation": f"sheet '{sheet.name}', cell {addr}",
                                })

        all_hits.sort(key=lambda h: h["score"], reverse=True)
        return all_hits[:max_results]

    def chunk(
        self,
        file_id: str,
        strategy: str = "section_aware",
        max_chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[Any]:
        """Chunk a document for retrieval pipelines."""
        from adx.chunking import ChunkingConfig, chunk_document

        graph = self.store.load_graph(file_id)
        if graph is None:
            raise ValueError(f"File {file_id} not found. Upload and process it first.")

        config = ChunkingConfig(
            strategy=strategy,
            max_chunk_size=max_chunk_size,
            overlap=overlap,
        )
        return chunk_document(graph, config)

    # ------------------------------------------------------------------
    # Inspection tools
    # ------------------------------------------------------------------

    def _inspector(self, file_id: str) -> DocumentInspector:
        graph = self.store.load_graph(file_id)
        if graph is None:
            raise ValueError(f"File {file_id} not found. Upload and process it first.")
        return DocumentInspector(graph)

    def profile(self, file_id: str) -> dict[str, Any]:
        """Profile a document."""
        return self._inspector(file_id).profile_document()

    def structure(self, file_id: str) -> dict[str, Any]:
        """Get document structure."""
        return self._inspector(file_id).list_structure()

    def search(self, file_id: str, query: str, max_results: int = 20) -> dict[str, Any]:
        """Search document content."""
        return self._inspector(file_id).search_document(query, max_results)

    def get_page(self, file_id: str, page_number: int) -> dict[str, Any]:
        """Inspect a specific page."""
        return self._inspector(file_id).get_page(page_number)

    def get_table(self, file_id: str, table_id: str) -> dict[str, Any]:
        """Inspect a specific table."""
        return self._inspector(file_id).get_table(table_id)

    def list_sheets(self, file_id: str) -> dict[str, Any]:
        """List workbook sheets."""
        return self._inspector(file_id).list_sheets()

    def read_range(self, file_id: str, sheet_name: str, cell_range: str) -> dict[str, Any]:
        """Read a spreadsheet range."""
        return self._inspector(file_id).read_range(sheet_name, cell_range)

    def find_cells(self, file_id: str, query: str, sheet_name: str | None = None) -> dict[str, Any]:
        """Find cells matching a query."""
        return self._inspector(file_id).find_cells(query, sheet_name)

    def inspect_formula(self, file_id: str, sheet_name: str, cell_address: str) -> dict[str, Any]:
        """Inspect a formula."""
        return self._inspector(file_id).inspect_formula(sheet_name, cell_address)

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def extract(
        self,
        file_id: str,
        schema: str | ExtractionSchema | dict[str, Any] | None = None,
        instructions: str | None = None,
    ) -> Extraction:
        """Extract structured data from a document."""
        graph = self.store.load_graph(file_id)
        if graph is None:
            raise ValueError(f"File {file_id} not found.")

        if isinstance(schema, dict):
            # JSON Schema input
            es = self.schema_registry.from_json_schema(
                schema_id="custom",
                name="Custom Schema",
                json_schema=schema,
            )
            schema = es

        if schema is None:
            # Auto-detect schema from document type
            doc_types = graph.document.likely_document_types
            from adx.models.document import DocumentType

            type_to_schema = {
                DocumentType.INVOICE: "invoice",
                DocumentType.CONTRACT: "contract",
                DocumentType.FINANCIAL_MODEL: "financial_model",
                DocumentType.SPREADSHEET: "financial_model",
            }
            for dt in doc_types:
                if dt in type_to_schema:
                    schema = type_to_schema[dt]
                    break
            if schema is None:
                schema = "table"

        extraction = self.extractor.extract(graph, schema, instructions)
        self.store.save_extraction(extraction)
        return extraction

    def validate(self, extraction_id: str) -> list[ValidationResult]:
        """Validate an extraction result."""
        extraction = self.store.load_extraction(extraction_id)
        if extraction is None:
            raise ValueError(f"Extraction {extraction_id} not found.")

        graph = self.store.load_graph(extraction.document_id)
        return self.validator.validate(extraction, graph)

    def get_extraction(self, extraction_id: str) -> Extraction | None:
        """Load a saved extraction."""
        return self.store.load_extraction(extraction_id)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(
        self,
        extraction_id: str,
        format: str = "json",
    ) -> str:
        """Export extraction results in the specified format."""
        extraction = self.store.load_extraction(extraction_id)
        if extraction is None:
            raise ValueError(f"Extraction {extraction_id} not found.")

        if format == "json":
            return extraction.model_dump_json(indent=2)
        elif format == "markdown":
            return self._export_markdown(extraction)
        elif format == "csv":
            return self._export_csv(extraction)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_markdown(self, extraction: Extraction) -> str:
        lines = [f"# Extraction: {extraction.schema_name or extraction.schema_id}\n"]
        for field in extraction.fields:
            citations = ", ".join(c.to_short_ref() for c in field.citations) or "no citation"
            lines.append(f"**{field.field_path}**: {field.value}")
            lines.append(f"  - confidence: {field.confidence:.2f}")
            lines.append(f"  - source: {citations}")
            if field.warnings:
                lines.append(f"  - warnings: {'; '.join(field.warnings)}")
            lines.append("")
        return "\n".join(lines)

    def _export_csv(self, extraction: Extraction) -> str:
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["field", "value", "confidence", "citation", "warnings"])
        for field in extraction.fields:
            citations = "; ".join(c.to_short_ref() for c in field.citations)
            warnings = "; ".join(field.warnings)
            writer.writerow([
                field.field_path,
                field.value,
                f"{field.confidence:.2f}",
                citations,
                warnings,
            ])
        return output.getvalue()
