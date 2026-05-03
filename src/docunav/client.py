"""DocuNav Python client — the main entry point for the SDK.

Usage:
    from docunav import DocuNav

    client = DocuNav()
    file = client.upload("invoice.pdf")
    profile = client.profile(file.id)
    result = client.extract(file.id, schema="invoice")
    validation = client.validate(result.id)
    print(result.output)
    print(result.fields[0].citations)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from docunav.extraction.extractor import Extractor
from docunav.extraction.schemas import ExtractionSchema, SchemaRegistry
from docunav.extraction.validator import Validator
from docunav.models.document import (
    DocumentGraph,
    Extraction,
    ValidationResult,
)
from docunav.parsers.graph_builder import GraphBuilder
from docunav.parsers.registry import ParserRegistry
from docunav.storage.store import DocumentStore
from docunav.tools.inspector import DocumentInspector


class DocuNav:
    """High-level client for the DocuNav document intelligence layer."""

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
            tmp_path.unlink(missing_ok=True)

    def get_graph(self, file_id: str) -> DocumentGraph | None:
        """Load a previously processed DocumentGraph."""
        return self.store.load_graph(file_id)

    def list_files(self) -> list[str]:
        """List all processed file IDs."""
        return self.store.list_graphs()

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
            from docunav.models.document import DocumentType

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
