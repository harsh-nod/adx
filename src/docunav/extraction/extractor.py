"""Rule-based extraction engine.

For MVP, extraction uses heuristic matching against the DocumentGraph.
LLM-based extraction is pluggable via the `llm_extract` method.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from docunav.models.document import (
    Citation,
    CitationType,
    DocumentGraph,
    Extraction,
    ExtractionField,
    FileType,
)
from docunav.extraction.schemas import ExtractionSchema, SchemaRegistry


class Extractor:
    """Extracts structured data from a DocumentGraph using a schema."""

    def __init__(self, schema_registry: SchemaRegistry | None = None) -> None:
        self.registry = schema_registry or SchemaRegistry()

    def extract(
        self,
        graph: DocumentGraph,
        schema: ExtractionSchema | str,
        instructions: str | None = None,
    ) -> Extraction:
        if isinstance(schema, str):
            resolved = self.registry.get(schema)
            if resolved is None:
                return Extraction(
                    document_id=graph.document.id,
                    status="error",
                    output={"error": f"Schema '{schema}' not found."},
                )
            schema = resolved

        extraction = Extraction(
            document_id=graph.document.id,
            schema_id=schema.id,
            schema_name=schema.name,
        )

        if graph.document.file_type == FileType.PDF:
            self._extract_from_pdf(graph, schema, extraction)
        elif graph.document.file_type in (FileType.XLSX, FileType.XLS, FileType.CSV):
            self._extract_from_spreadsheet(graph, schema, extraction)

        # Build output dict from fields
        for field in extraction.fields:
            extraction.output[field.field_path] = field.value

        # Compute overall confidence
        if extraction.fields:
            extraction.confidence = sum(f.confidence for f in extraction.fields) / len(
                extraction.fields
            )

        return extraction

    def _extract_from_pdf(
        self,
        graph: DocumentGraph,
        schema: ExtractionSchema,
        extraction: Extraction,
    ) -> None:
        full_text = graph.get_all_text()
        all_tables = graph.get_all_tables()

        for field_def in schema.fields:
            value, confidence, citation = self._find_field_in_text(
                field_def.name,
                field_def.field_type,
                full_text,
                graph,
            )

            # Try tables if text didn't work
            if value is None and all_tables:
                for table in all_tables:
                    val, conf, cit = self._find_field_in_table(
                        field_def.name, table, graph
                    )
                    if val is not None:
                        value, confidence, citation = val, conf, cit
                        break

            warnings: list[str] = []
            if value is None:
                if field_def.required:
                    warnings.append(f"Required field '{field_def.name}' not found.")
                confidence = 0.0

            citations = [citation] if citation else []
            if not citations and value is not None:
                warnings.append(f"No citation found for field '{field_def.name}'.")

            extraction.fields.append(ExtractionField(
                field_path=field_def.name,
                value=value,
                confidence=confidence,
                citations=citations,
                warnings=warnings,
            ))

    def _extract_from_spreadsheet(
        self,
        graph: DocumentGraph,
        schema: ExtractionSchema,
        extraction: Extraction,
    ) -> None:
        if not graph.workbook:
            return

        for field_def in schema.fields:
            value = None
            confidence = 0.0
            citation = None
            warnings: list[str] = []

            # Search cells for field name
            for sheet in graph.workbook.sheets:
                for table in sheet.tables:
                    for cell in table.cells:
                        cell_val_lower = str(cell.value).lower()
                        field_name_lower = field_def.name.replace("_", " ").lower()

                        if field_name_lower in cell_val_lower:
                            # Look for the value in adjacent cell (same row, next column)
                            adjacent = [
                                c for c in table.cells
                                if c.row_index == cell.row_index
                                and c.column_index == cell.column_index + 1
                            ]
                            if adjacent:
                                value = adjacent[0].value
                                confidence = 0.8
                                citation = Citation(
                                    document_id=graph.document.id,
                                    target_object_id=adjacent[0].id,
                                    citation_type=CitationType.CELL,
                                    sheet_name=sheet.name,
                                    cell_address=adjacent[0].source_cell_ref,
                                    text_snippet=str(value)[:200],
                                )
                                break
                if value is not None:
                    break

            if value is None and field_def.required:
                warnings.append(f"Required field '{field_def.name}' not found in spreadsheet.")

            citations = [citation] if citation else []
            extraction.fields.append(ExtractionField(
                field_path=field_def.name,
                value=value,
                confidence=confidence,
                citations=citations,
                warnings=warnings,
            ))

    def _find_field_in_text(
        self,
        field_name: str,
        field_type: str,
        full_text: str,
        graph: DocumentGraph,
    ) -> tuple[Any, float, Citation | None]:
        """Heuristic: find a field value near its label in the document text."""
        label_variants = self._label_variants(field_name)

        for label in label_variants:
            pattern = re.compile(
                rf"(?i){re.escape(label)}\s*[:\-]?\s*(.+?)(?:\n|$)"
            )
            match = pattern.search(full_text)
            if match:
                raw_value = match.group(1).strip()
                value = self._coerce(raw_value, field_type)

                # Find the page containing this text
                citation = None
                for page in graph.pages:
                    for block in page.text_blocks:
                        if label.lower() in block.text.lower():
                            citation = Citation(
                                document_id=graph.document.id,
                                target_object_id=block.id,
                                citation_type=CitationType.TEXT_SPAN,
                                page_number=page.page_number,
                                bounding_box=block.bounding_box,
                                text_snippet=block.text[:200],
                            )
                            break
                    if citation:
                        break

                return value, 0.85, citation

        return None, 0.0, None

    def _find_field_in_table(
        self,
        field_name: str,
        table: Any,
        graph: DocumentGraph,
    ) -> tuple[Any, float, Citation | None]:
        """Look for field in table headers and get corresponding values."""
        label_variants = self._label_variants(field_name)

        # Check if any header matches
        header_cells = [c for c in table.cells if c.row_index == 0]
        for header_cell in header_cells:
            for label in label_variants:
                if label.lower() in header_cell.value.lower():
                    # Get all values in this column
                    col_values = [
                        c.value
                        for c in table.cells
                        if c.column_index == header_cell.column_index and c.row_index > 0
                    ]
                    if col_values:
                        citation = Citation(
                            document_id=graph.document.id,
                            target_object_id=table.id,
                            citation_type=CitationType.TABLE,
                            page_number=table.page_number,
                            text_snippet=f"Column '{header_cell.value}'",
                        )
                        return col_values if len(col_values) > 1 else col_values[0], 0.8, citation

        return None, 0.0, None

    def _label_variants(self, field_name: str) -> list[str]:
        """Generate search variants from a field name."""
        base = field_name.replace("_", " ")
        variants = [base, base.title(), base.upper()]

        custom_mappings: dict[str, list[str]] = {
            "vendor_name": ["vendor", "supplier", "from", "bill from", "sold by"],
            "invoice_number": ["invoice #", "invoice no", "inv no", "inv #", "invoice number"],
            "invoice_date": ["invoice date", "date", "inv date"],
            "due_date": ["due date", "payment due", "due by"],
            "purchase_order": ["po", "po #", "purchase order", "po number"],
            "subtotal": ["subtotal", "sub total", "sub-total"],
            "total": ["total", "amount due", "total due", "total amount", "balance due", "grand total"],
            "tax": ["tax", "vat", "gst", "sales tax", "tax amount"],
            "payment_terms": ["payment terms", "terms", "net 30", "net 60"],
        }

        if field_name in custom_mappings:
            variants.extend(custom_mappings[field_name])

        return variants

    def _coerce(self, value: str, field_type: str) -> Any:
        """Attempt to coerce a string value to the expected type."""
        if field_type in ("number", "currency"):
            cleaned = re.sub(r"[^\d.\-,]", "", value)
            cleaned = cleaned.replace(",", "")
            try:
                return float(cleaned)
            except ValueError:
                return value
        if field_type == "integer":
            cleaned = re.sub(r"[^\d\-]", "", value)
            try:
                return int(cleaned)
            except ValueError:
                return value
        return value
