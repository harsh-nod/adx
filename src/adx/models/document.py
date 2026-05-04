"""Canonical document model.

Every parser output is normalized into this model. Every extracted field
traces back to citations in this model. This is the single source of truth
for document structure within ADX.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


SCHEMA_VERSION = "0.1.0"


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FileType(str, Enum):
    PDF = "pdf"
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    DOCX = "docx"
    PPTX = "pptx"
    RTF = "rtf"
    IMAGE = "image"
    TEXT = "text"
    UNKNOWN = "unknown"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class DocumentType(str, Enum):
    INVOICE = "invoice"
    CONTRACT = "contract"
    FINANCIAL_MODEL = "financial_model"
    BANK_STATEMENT = "bank_statement"
    RESUME = "resume"
    INSURANCE_CLAIM = "insurance_claim"
    REPORT = "report"
    LETTER = "letter"
    FORM = "form"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    UNKNOWN = "unknown"


class TextBlockType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    HEADER = "header"
    FOOTER = "footer"
    PAGE_NUMBER = "page_number"
    OTHER = "other"


class CitationType(str, Enum):
    PAGE = "page"
    BOUNDING_BOX = "bounding_box"
    TEXT_SPAN = "text_span"
    TABLE = "table"
    CELL = "cell"
    CELL_RANGE = "cell_range"
    SECTION = "section"
    FORMULA = "formula"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


# ---------------------------------------------------------------------------
# Core document entities
# ---------------------------------------------------------------------------

class TextBlock(BaseModel):
    id: str = Field(default_factory=_new_id)
    page_number: int | None = None
    text: str = ""
    block_type: TextBlockType = TextBlockType.PARAGRAPH
    bounding_box: BoundingBox | None = None
    reading_order_index: int = 0
    confidence: float = 1.0
    source_parser: str = ""


class TableCell(BaseModel):
    id: str = Field(default_factory=_new_id)
    row_index: int = 0
    column_index: int = 0
    value: str = ""
    normalized_value: Any = None
    data_type: str = "string"
    row_span: int = 1
    column_span: int = 1
    bounding_box: BoundingBox | None = None
    source_cell_ref: str | None = None
    confidence: float = 1.0


class Table(BaseModel):
    id: str = Field(default_factory=_new_id)
    page_number: int | None = None
    sheet_name: str | None = None
    title: str | None = None
    row_count: int = 0
    column_count: int = 0
    cells: list[TableCell] = Field(default_factory=list)
    bounding_box: BoundingBox | None = None
    cell_range: str | None = None
    confidence: float = 1.0
    source_parser: str = ""
    continued_from_table_id: str | None = None
    continued_to_table_id: str | None = None

    def to_rows(self) -> list[list[str]]:
        """Return cell values as a 2D list."""
        if not self.cells:
            return []
        grid: list[list[str]] = [
            ["" for _ in range(self.column_count)] for _ in range(self.row_count)
        ]
        for cell in self.cells:
            if cell.row_index < self.row_count and cell.column_index < self.column_count:
                grid[cell.row_index][cell.column_index] = cell.value
        return grid

    def to_markdown(self) -> str:
        rows = self.to_rows()
        if not rows:
            return ""
        lines: list[str] = []
        header = "| " + " | ".join(rows[0]) + " |"
        sep = "| " + " | ".join("---" for _ in rows[0]) + " |"
        lines.append(header)
        lines.append(sep)
        for row in rows[1:]:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)


class Figure(BaseModel):
    id: str = Field(default_factory=_new_id)
    page_number: int | None = None
    caption: str | None = None
    figure_type: str = "image"
    bounding_box: BoundingBox | None = None
    confidence: float = 1.0


class Page(BaseModel):
    id: str = Field(default_factory=_new_id)
    page_number: int = 0
    width: float = 0.0
    height: float = 0.0
    rotation: int = 0
    text_blocks: list[TextBlock] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    detected_language: str | None = None
    ocr_used: bool = False
    ocr_confidence: float | None = None

    @property
    def full_text(self) -> str:
        return "\n".join(
            tb.text for tb in sorted(self.text_blocks, key=lambda b: b.reading_order_index)
        )


class Section(BaseModel):
    id: str = Field(default_factory=_new_id)
    title: str = ""
    heading_level: int = 1
    parent_section_id: str | None = None
    start_page: int | None = None
    end_page: int | None = None
    text_block_ids: list[str] = Field(default_factory=list)
    table_ids: list[str] = Field(default_factory=list)
    figure_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Spreadsheet entities
# ---------------------------------------------------------------------------

class SpreadsheetCell(BaseModel):
    id: str = Field(default_factory=_new_id)
    sheet_name: str = ""
    address: str = ""
    value: Any = None
    formula: str | None = None
    data_type: str = "string"
    number_format: str | None = None
    is_hidden: bool = False
    is_merged: bool = False
    comment: str | None = None
    confidence: float = 1.0


class Formula(BaseModel):
    id: str = Field(default_factory=_new_id)
    sheet_name: str = ""
    cell_address: str = ""
    formula_text: str = ""
    referenced_cells: list[str] = Field(default_factory=list)
    referenced_ranges: list[str] = Field(default_factory=list)
    referenced_sheets: list[str] = Field(default_factory=list)
    external_references: list[str] = Field(default_factory=list)
    calculated_value: Any = None
    parse_status: str = "ok"


class Sheet(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str = ""
    index: int = 0
    is_visible: bool = True
    used_range: str | None = None
    row_count: int = 0
    column_count: int = 0
    tables: list[Table] = Field(default_factory=list)
    formulas: list[Formula] = Field(default_factory=list)
    merged_cells: list[str] = Field(default_factory=list)
    hidden_rows: list[int] = Field(default_factory=list)
    hidden_columns: list[int] = Field(default_factory=list)
    comments: list[dict[str, str]] = Field(default_factory=list)


class Workbook(BaseModel):
    id: str = Field(default_factory=_new_id)
    sheets: list[Sheet] = Field(default_factory=list)
    named_ranges: dict[str, str] = Field(default_factory=dict)
    external_links: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Citation and provenance
# ---------------------------------------------------------------------------

class Citation(BaseModel):
    id: str = Field(default_factory=_new_id)
    document_id: str = ""
    target_object_id: str = ""
    citation_type: CitationType = CitationType.PAGE
    page_number: int | None = None
    bounding_box: BoundingBox | None = None
    sheet_name: str | None = None
    cell_address: str | None = None
    cell_range: str | None = None
    text_snippet: str | None = None
    confidence: float = 1.0

    def to_short_ref(self) -> str:
        parts: list[str] = []
        if self.page_number is not None:
            parts.append(f"page {self.page_number}")
        if self.sheet_name:
            parts.append(f"sheet '{self.sheet_name}'")
        if self.cell_address:
            parts.append(f"cell {self.cell_address}")
        if self.cell_range:
            parts.append(f"range {self.cell_range}")
        return ", ".join(parts) if parts else "unknown location"


# ---------------------------------------------------------------------------
# Extraction and validation
# ---------------------------------------------------------------------------

class ExtractionField(BaseModel):
    field_path: str = ""
    value: Any = None
    confidence: float = 1.0
    citations: list[Citation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Extraction(BaseModel):
    id: str = Field(default_factory=_new_id)
    document_id: str = ""
    schema_id: str | None = None
    schema_name: str | None = None
    status: str = "completed"
    output: dict[str, Any] = Field(default_factory=dict)
    fields: list[ExtractionField] = Field(default_factory=list)
    confidence: float = 1.0
    model_used: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationResult(BaseModel):
    id: str = Field(default_factory=_new_id)
    extraction_id: str = ""
    severity: ValidationSeverity = ValidationSeverity.WARNING
    rule_name: str = ""
    message: str = ""
    affected_fields: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    status: str = "open"


# ---------------------------------------------------------------------------
# Confidence summary
# ---------------------------------------------------------------------------

class ConfidenceSummary(BaseModel):
    overall: float = 1.0
    text_confidence: float = 1.0
    table_confidence: float = 1.0
    ocr_confidence: float | None = None
    formula_confidence: float | None = None
    low_confidence_regions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level document
# ---------------------------------------------------------------------------

class Document(BaseModel):
    id: str = Field(default_factory=_new_id)
    filename: str = ""
    file_type: FileType = FileType.UNKNOWN
    mime_type: str = ""
    checksum: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_uri: str | None = None
    page_count: int = 0
    sheet_count: int = 0
    parser_used: str = ""
    parser_version: str = ""
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    confidence_summary: ConfidenceSummary = Field(default_factory=ConfidenceSummary)
    metadata: dict[str, Any] = Field(default_factory=dict)
    likely_document_types: list[DocumentType] = Field(default_factory=list)

    @staticmethod
    def compute_checksum(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# DocumentGraph — the unified representation
# ---------------------------------------------------------------------------

class DocumentGraph(BaseModel):
    """The canonical, parser-agnostic representation of a processed document."""

    schema_version: str = SCHEMA_VERSION
    document: Document = Field(default_factory=Document)
    pages: list[Page] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    workbook: Workbook | None = None
    citations: list[Citation] = Field(default_factory=list)

    def get_page(self, page_number: int) -> Page | None:
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None

    def get_all_tables(self) -> list[Table]:
        tables: list[Table] = []
        for page in self.pages:
            tables.extend(page.tables)
        if self.workbook:
            for sheet in self.workbook.sheets:
                tables.extend(sheet.tables)
        return tables

    def get_table_by_id(self, table_id: str) -> Table | None:
        for table in self.get_all_tables():
            if table.id == table_id:
                return table
        return None

    def get_all_text(self) -> str:
        parts: list[str] = []
        for page in sorted(self.pages, key=lambda p: p.page_number):
            parts.append(page.full_text)
        return "\n\n".join(parts)

    def get_sheet(self, name: str) -> Sheet | None:
        if not self.workbook:
            return None
        for sheet in self.workbook.sheets:
            if sheet.name == name:
                return sheet
        return None

    def search_text(self, query: str) -> list[tuple[TextBlock, int]]:
        """Simple case-insensitive substring search. Returns (block, page_number) pairs."""
        query_lower = query.lower()
        results: list[tuple[TextBlock, int]] = []
        for page in self.pages:
            for block in page.text_blocks:
                if query_lower in block.text.lower():
                    results.append((block, page.page_number))
        return results

    def to_markdown(self) -> str:
        """Render the document graph as markdown."""
        lines: list[str] = []

        # Title from document filename
        lines.append(f"# {self.document.filename}\n")

        # Render pages (PDF, DOCX, PPTX, RTF)
        for page in sorted(self.pages, key=lambda p: p.page_number):
            sorted_blocks = sorted(page.text_blocks, key=lambda b: b.reading_order_index)
            for block in sorted_blocks:
                if block.block_type == TextBlockType.HEADING:
                    # Determine heading level from sections
                    level = self._heading_level_for_block(block)
                    lines.append(f"\n{'#' * (level + 1)} {block.text}\n")
                elif block.block_type == TextBlockType.LIST_ITEM:
                    lines.append(f"- {block.text}")
                elif block.block_type == TextBlockType.FOOTNOTE:
                    lines.append(f"\n> *{block.text}*\n")
                elif block.block_type in (TextBlockType.HEADER, TextBlockType.FOOTER, TextBlockType.PAGE_NUMBER):
                    continue
                else:
                    lines.append(block.text)

            for table in page.tables:
                md = table.to_markdown()
                if md:
                    lines.append("")
                    lines.append(md)
                    lines.append("")

        # Render workbook sheets
        if self.workbook:
            for sheet in self.workbook.sheets:
                lines.append(f"\n## Sheet: {sheet.name}\n")
                for table in sheet.tables:
                    md = table.to_markdown()
                    if md:
                        lines.append(md)
                        lines.append("")

        return "\n".join(lines)

    def _heading_level_for_block(self, block: TextBlock) -> int:
        """Find the heading level from sections, or default to 2."""
        for section in self.sections:
            if block.text.strip() == section.title:
                return section.heading_level
        return 2

    def search_cells(self, query: str) -> list[SpreadsheetCell]:
        """Search spreadsheet cell values."""
        if not self.workbook:
            return []
        query_lower = query.lower()
        results: list[SpreadsheetCell] = []
        for sheet in self.workbook.sheets:
            for table in sheet.tables:
                for cell in table.cells:
                    if query_lower in str(cell.value).lower():
                        results.append(
                            SpreadsheetCell(
                                sheet_name=sheet.name,
                                address=cell.source_cell_ref or f"R{cell.row_index}C{cell.column_index}",
                                value=cell.value,
                            )
                        )
        return results


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

class BatchResult(BaseModel):
    """Result of a batch directory upload operation."""

    total_files: int = 0
    successful: int = 0
    failed: int = 0
    graphs: list[str] = Field(default_factory=list)
    errors: dict[str, str] = Field(default_factory=dict)
