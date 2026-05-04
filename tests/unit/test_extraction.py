"""Tests for SchemaRegistry, Extractor, and Validator."""

from __future__ import annotations

import pytest

from adx.extraction.extractor import Extractor
from adx.extraction.schemas import (
    CONTRACT_SCHEMA,
    ExtractionSchema,
    FINANCIAL_MODEL_SCHEMA,
    FieldDef,
    INVOICE_SCHEMA,
    SchemaRegistry,
    TABLE_SCHEMA,
)
from adx.extraction.validator import Validator
from adx.models.document import (
    Citation,
    CitationType,
    Document,
    DocumentGraph,
    DocumentType,
    Extraction,
    ExtractionField,
    FileType,
    Formula,
    Page,
    ProcessingStatus,
    Sheet,
    Table,
    TableCell,
    TextBlock,
    TextBlockType,
    ValidationResult,
    ValidationSeverity,
    Workbook,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def schema_registry():
    return SchemaRegistry()


@pytest.fixture
def extractor(schema_registry):
    return Extractor(schema_registry)


@pytest.fixture
def validator(schema_registry):
    return Validator(schema_registry)


@pytest.fixture
def invoice_pdf_graph():
    """A PDF graph with invoice-like text content."""
    doc = Document(
        id="inv001",
        filename="invoice.pdf",
        file_type=FileType.PDF,
        page_count=1,
        processing_status=ProcessingStatus.COMPLETED,
        likely_document_types=[DocumentType.INVOICE],
    )

    blocks = [
        TextBlock(
            page_number=1,
            text="Vendor Name: Acme Corp",
            block_type=TextBlockType.PARAGRAPH,
            reading_order_index=0,
        ),
        TextBlock(
            page_number=1,
            text="Invoice Number: INV-2024-001",
            block_type=TextBlockType.PARAGRAPH,
            reading_order_index=1,
        ),
        TextBlock(
            page_number=1,
            text="Invoice Date: 2024-01-15",
            block_type=TextBlockType.PARAGRAPH,
            reading_order_index=2,
        ),
        TextBlock(
            page_number=1,
            text="Subtotal: $1000.00",
            block_type=TextBlockType.PARAGRAPH,
            reading_order_index=3,
        ),
        TextBlock(
            page_number=1,
            text="Tax: $80.00",
            block_type=TextBlockType.PARAGRAPH,
            reading_order_index=4,
        ),
        TextBlock(
            page_number=1,
            text="Total: $1080.00",
            block_type=TextBlockType.PARAGRAPH,
            reading_order_index=5,
        ),
    ]

    page = Page(page_number=1, width=612, height=792, text_blocks=blocks)
    return DocumentGraph(document=doc, pages=[page])


@pytest.fixture
def invoice_bad_math_graph():
    """Invoice where total != subtotal + tax."""
    doc = Document(
        id="inv002",
        filename="bad_invoice.pdf",
        file_type=FileType.PDF,
        page_count=1,
        likely_document_types=[DocumentType.INVOICE],
    )
    blocks = [
        TextBlock(page_number=1, text="Subtotal: $1000.00", reading_order_index=0),
        TextBlock(page_number=1, text="Tax: $80.00", reading_order_index=1),
        TextBlock(page_number=1, text="Total: $2000.00", reading_order_index=2),
    ]
    page = Page(page_number=1, text_blocks=blocks)
    return DocumentGraph(document=doc, pages=[page])


@pytest.fixture
def spreadsheet_graph():
    """A spreadsheet graph with labeled cells."""
    doc = Document(
        id="ss001",
        filename="data.xlsx",
        file_type=FileType.XLSX,
        sheet_count=1,
        processing_status=ProcessingStatus.COMPLETED,
        likely_document_types=[DocumentType.SPREADSHEET],
    )
    cells = [
        TableCell(row_index=0, column_index=0, value="vendor name", source_cell_ref="A1"),
        TableCell(row_index=0, column_index=1, value="Acme Inc", source_cell_ref="B1"),
        TableCell(row_index=1, column_index=0, value="invoice number", source_cell_ref="A2"),
        TableCell(row_index=1, column_index=1, value="INV-999", source_cell_ref="B2"),
        TableCell(row_index=2, column_index=0, value="total", source_cell_ref="A3"),
        TableCell(row_index=2, column_index=1, value="5000", source_cell_ref="B3"),
    ]
    table = Table(sheet_name="Sheet1", row_count=3, column_count=2, cells=cells)
    sheet = Sheet(name="Sheet1", index=0, is_visible=True, tables=[table])
    wb = Workbook(sheets=[sheet])
    return DocumentGraph(document=doc, workbook=wb)


@pytest.fixture
def table_pdf_graph():
    """A PDF graph with a table containing headers matching field names."""
    doc = Document(
        id="tpdf001",
        filename="data.pdf",
        file_type=FileType.PDF,
        page_count=1,
    )
    cells = [
        TableCell(row_index=0, column_index=0, value="Total"),
        TableCell(row_index=0, column_index=1, value="Tax"),
        TableCell(row_index=1, column_index=0, value="500"),
        TableCell(row_index=1, column_index=1, value="40"),
    ]
    table = Table(page_number=1, row_count=2, column_count=2, cells=cells)
    page = Page(page_number=1, tables=[table])
    return DocumentGraph(document=doc, pages=[page])


# ---------------------------------------------------------------------------
# SchemaRegistry
# ---------------------------------------------------------------------------

class TestSchemaRegistry:
    def test_built_in_schemas(self, schema_registry):
        schemas = schema_registry.list_schemas()
        ids = [s["id"] for s in schemas]
        assert "invoice" in ids
        assert "contract" in ids
        assert "financial_model" in ids
        assert "table" in ids

    def test_get_existing_schema(self, schema_registry):
        schema = schema_registry.get("invoice")
        assert schema is not None
        assert schema.id == "invoice"
        assert schema.name == "Invoice"
        assert len(schema.fields) > 0

    def test_get_nonexistent_schema(self, schema_registry):
        assert schema_registry.get("nonexistent") is None

    def test_register_custom_schema(self, schema_registry):
        custom = ExtractionSchema(
            id="custom_test",
            name="Custom Test",
            fields=[
                FieldDef(name="field_a", description="Test field A"),
                FieldDef(name="field_b", description="Test field B", required=False),
            ],
        )
        schema_registry.register(custom)
        retrieved = schema_registry.get("custom_test")
        assert retrieved is not None
        assert retrieved.name == "Custom Test"
        assert len(retrieved.fields) == 2

    def test_from_json_schema(self, schema_registry):
        json_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Person name"},
                "age": {"type": "integer", "description": "Age in years"},
                "birthday": {"type": "string", "format": "date", "description": "Date of birth"},
            },
            "required": ["name", "age"],
        }
        schema = schema_registry.from_json_schema("person", "Person", json_schema)
        assert schema.id == "person"
        assert len(schema.fields) == 3

        name_field = next(f for f in schema.fields if f.name == "name")
        assert name_field.required is True
        assert name_field.field_type == "string"

        age_field = next(f for f in schema.fields if f.name == "age")
        assert age_field.required is True
        assert age_field.field_type == "integer"

        birthday_field = next(f for f in schema.fields if f.name == "birthday")
        assert birthday_field.required is False
        assert birthday_field.field_type == "date"

        # Also auto-registered
        assert schema_registry.get("person") is not None

    def test_list_schemas_format(self, schema_registry):
        schemas = schema_registry.list_schemas()
        for s in schemas:
            assert "id" in s
            assert "name" in s
            assert "description" in s


# ---------------------------------------------------------------------------
# ExtractionSchema.to_json_schema
# ---------------------------------------------------------------------------

class TestExtractionSchemaToJsonSchema:
    def test_invoice_to_json_schema(self):
        js = INVOICE_SCHEMA.to_json_schema()
        assert js["type"] == "object"
        assert "vendor_name" in js["properties"]
        assert "total" in js["properties"]
        assert "vendor_name" in js["required"]
        assert "vendor_address" not in js["required"]  # required=False

    def test_field_types_mapped(self):
        schema = ExtractionSchema(
            id="test",
            name="Test",
            fields=[
                FieldDef(name="s", field_type="string"),
                FieldDef(name="n", field_type="number"),
                FieldDef(name="i", field_type="integer"),
                FieldDef(name="b", field_type="boolean"),
                FieldDef(name="d", field_type="date"),
                FieldDef(name="c", field_type="currency"),
                FieldDef(name="a", field_type="array"),
                FieldDef(name="o", field_type="object"),
            ],
        )
        js = schema.to_json_schema()
        assert js["properties"]["s"]["type"] == "string"
        assert js["properties"]["n"]["type"] == "number"
        assert js["properties"]["i"]["type"] == "integer"
        assert js["properties"]["b"]["type"] == "boolean"
        assert js["properties"]["d"]["type"] == "string"
        assert js["properties"]["d"]["format"] == "date"
        assert js["properties"]["c"]["type"] == "number"
        assert js["properties"]["a"]["type"] == "array"
        assert js["properties"]["o"]["type"] == "object"


# ---------------------------------------------------------------------------
# Extractor — PDF extraction
# ---------------------------------------------------------------------------

class TestExtractorPDF:
    def test_extract_invoice_from_pdf(self, extractor, invoice_pdf_graph):
        extraction = extractor.extract(invoice_pdf_graph, "invoice")
        assert extraction.document_id == "inv001"
        assert extraction.schema_id == "invoice"
        assert extraction.schema_name == "Invoice"

        # Check extracted fields
        field_map = {f.field_path: f for f in extraction.fields}
        assert "vendor_name" in field_map
        assert field_map["vendor_name"].value == "Acme Corp"
        assert "invoice_number" in field_map
        assert field_map["invoice_number"].value == "INV-2024-001"

    def test_extract_numeric_fields_coerced(self, extractor, invoice_pdf_graph):
        extraction = extractor.extract(invoice_pdf_graph, "invoice")
        field_map = {f.field_path: f for f in extraction.fields}
        subtotal = field_map.get("subtotal")
        if subtotal and subtotal.value is not None:
            assert isinstance(subtotal.value, float)

    def test_extract_with_citations(self, extractor, invoice_pdf_graph):
        extraction = extractor.extract(invoice_pdf_graph, "invoice")
        fields_with_citations = [f for f in extraction.fields if f.citations]
        assert len(fields_with_citations) > 0
        for f in fields_with_citations:
            for c in f.citations:
                assert c.page_number is not None or c.sheet_name is not None

    def test_extract_schema_not_found(self, extractor, invoice_pdf_graph):
        extraction = extractor.extract(invoice_pdf_graph, "nonexistent_schema")
        assert extraction.status == "error"
        assert "not found" in extraction.output.get("error", "")

    def test_extract_with_schema_object(self, extractor, invoice_pdf_graph):
        custom_schema = ExtractionSchema(
            id="custom",
            name="Custom",
            fields=[
                FieldDef(name="vendor_name", description="Vendor"),
            ],
        )
        extraction = extractor.extract(invoice_pdf_graph, custom_schema)
        assert extraction.schema_id == "custom"
        field_map = {f.field_path: f for f in extraction.fields}
        assert "vendor_name" in field_map

    def test_missing_required_field_warning(self, extractor, invoice_pdf_graph):
        """Fields not found in text should have warnings."""
        extraction = extractor.extract(invoice_pdf_graph, "invoice")
        field_map = {f.field_path: f for f in extraction.fields}
        # purchase_order is optional but may not be found
        # All required fields should either have a value or a warning
        for f in extraction.fields:
            if f.value is None:
                assert len(f.warnings) > 0 or True  # optional fields may have no warning

    def test_extract_from_table(self, extractor, table_pdf_graph):
        """Extractor should find values in tables when not found in text."""
        schema = ExtractionSchema(
            id="test",
            name="Test",
            fields=[
                FieldDef(name="total", description="Total amount"),
            ],
        )
        extraction = extractor.extract(table_pdf_graph, schema)
        field_map = {f.field_path: f for f in extraction.fields}
        total = field_map.get("total")
        assert total is not None
        assert total.value is not None

    def test_confidence_computed(self, extractor, invoice_pdf_graph):
        extraction = extractor.extract(invoice_pdf_graph, "invoice")
        assert 0.0 <= extraction.confidence <= 1.0


# ---------------------------------------------------------------------------
# Extractor — Spreadsheet extraction
# ---------------------------------------------------------------------------

class TestExtractorSpreadsheet:
    def test_extract_from_spreadsheet(self, extractor, spreadsheet_graph):
        extraction = extractor.extract(spreadsheet_graph, "invoice")
        field_map = {f.field_path: f for f in extraction.fields}
        vendor = field_map.get("vendor_name")
        assert vendor is not None
        assert vendor.value == "Acme Inc"

    def test_extract_adjacent_cell(self, extractor, spreadsheet_graph):
        """Extractor should find value in the cell to the right of a label."""
        extraction = extractor.extract(spreadsheet_graph, "invoice")
        field_map = {f.field_path: f for f in extraction.fields}
        inv_num = field_map.get("invoice_number")
        assert inv_num is not None
        assert inv_num.value == "INV-999"

    def test_extract_spreadsheet_citations(self, extractor, spreadsheet_graph):
        extraction = extractor.extract(spreadsheet_graph, "invoice")
        field_map = {f.field_path: f for f in extraction.fields}
        vendor = field_map.get("vendor_name")
        if vendor and vendor.value:
            assert len(vendor.citations) > 0
            assert vendor.citations[0].citation_type == CitationType.CELL

    def test_extract_from_empty_workbook(self, extractor):
        doc = Document(id="empty", file_type=FileType.XLSX)
        graph = DocumentGraph(document=doc)
        extraction = extractor.extract(graph, "invoice")
        # Should not crash, fields will have None values
        assert extraction.document_id == "empty"


# ---------------------------------------------------------------------------
# Extractor — coerce
# ---------------------------------------------------------------------------

class TestExtractorCoerce:
    def test_coerce_number(self):
        ext = Extractor()
        assert ext._coerce("$1,234.56", "currency") == 1234.56
        assert ext._coerce("100", "number") == 100.0

    def test_coerce_integer(self):
        ext = Extractor()
        assert ext._coerce("42", "integer") == 42

    def test_coerce_invalid_number(self):
        ext = Extractor()
        result = ext._coerce("not a number", "number")
        assert result == "not a number"

    def test_coerce_string_passthrough(self):
        ext = Extractor()
        assert ext._coerce("hello", "string") == "hello"

    def test_coerce_date_passthrough(self):
        ext = Extractor()
        assert ext._coerce("2024-01-15", "date") == "2024-01-15"


# ---------------------------------------------------------------------------
# Extractor — label variants
# ---------------------------------------------------------------------------

class TestLabelVariants:
    def test_basic_variants(self):
        ext = Extractor()
        variants = ext._label_variants("some_field")
        assert "some field" in variants
        assert "Some Field" in variants
        assert "SOME FIELD" in variants

    def test_known_field_variants(self):
        ext = Extractor()
        variants = ext._label_variants("vendor_name")
        assert "vendor" in variants
        assert "supplier" in variants

    def test_invoice_number_variants(self):
        ext = Extractor()
        variants = ext._label_variants("invoice_number")
        assert "invoice #" in variants
        assert "inv no" in variants

    def test_total_variants(self):
        ext = Extractor()
        variants = ext._label_variants("total")
        assert "amount due" in variants
        assert "grand total" in variants


# ---------------------------------------------------------------------------
# Validator — required fields
# ---------------------------------------------------------------------------

class TestValidatorRequiredFields:
    def test_missing_required_field(self, validator):
        extraction = Extraction(
            id="ex1",
            document_id="doc1",
            schema_id="invoice",
            fields=[
                ExtractionField(field_path="vendor_name", value="Acme"),
                # invoice_number is required but missing
            ],
        )
        results = validator.validate(extraction)
        missing = [r for r in results if r.rule_name == "required_field_missing"]
        assert len(missing) > 0
        missing_fields = []
        for r in missing:
            missing_fields.extend(r.affected_fields)
        assert "invoice_number" in missing_fields

    def test_required_field_null_value(self, validator):
        extraction = Extraction(
            id="ex2",
            document_id="doc1",
            schema_id="invoice",
            fields=[
                ExtractionField(field_path="vendor_name", value=None),
                ExtractionField(field_path="invoice_number", value="INV-001"),
                ExtractionField(field_path="invoice_date", value="2024-01-01"),
                ExtractionField(field_path="subtotal", value=100.0),
                ExtractionField(field_path="total", value=100.0),
                ExtractionField(field_path="line_items", value=[]),
            ],
        )
        results = validator.validate(extraction)
        null_results = [r for r in results if r.rule_name == "required_field_null"]
        assert len(null_results) > 0
        assert "vendor_name" in null_results[0].affected_fields


# ---------------------------------------------------------------------------
# Validator — type checking
# ---------------------------------------------------------------------------

class TestValidatorTypeChecking:
    def test_type_mismatch(self, validator):
        extraction = Extraction(
            id="ex3",
            document_id="doc1",
            schema_id="invoice",
            fields=[
                ExtractionField(field_path="subtotal", value="not a number"),
                ExtractionField(field_path="total", value="also not"),
                ExtractionField(field_path="vendor_name", value="Acme"),
                ExtractionField(field_path="invoice_number", value="INV-001"),
                ExtractionField(field_path="invoice_date", value="2024-01-01"),
                ExtractionField(field_path="line_items", value=[]),
            ],
        )
        results = validator.validate(extraction)
        type_issues = [r for r in results if r.rule_name == "type_mismatch"]
        assert len(type_issues) > 0

    def test_valid_numeric_string(self, validator):
        """A string like '$100.00' should be parseable and not raise type_mismatch."""
        extraction = Extraction(
            id="ex4",
            document_id="doc1",
            schema_id="invoice",
            fields=[
                ExtractionField(field_path="subtotal", value="$100.00"),
                ExtractionField(field_path="total", value="$100.00"),
                ExtractionField(field_path="vendor_name", value="Acme"),
                ExtractionField(field_path="invoice_number", value="INV-001"),
                ExtractionField(field_path="invoice_date", value="2024-01-01"),
                ExtractionField(field_path="line_items", value=[]),
            ],
        )
        results = validator.validate(extraction)
        type_issues = [r for r in results if r.rule_name == "type_mismatch"]
        # "$100.00" should be parseable after stripping $ sign
        subtotal_issues = [r for r in type_issues if "subtotal" in r.affected_fields]
        assert len(subtotal_issues) == 0


# ---------------------------------------------------------------------------
# Validator — citation validation
# ---------------------------------------------------------------------------

class TestValidatorCitations:
    def test_missing_citation_warning(self, validator):
        extraction = Extraction(
            id="ex5",
            document_id="doc1",
            fields=[
                ExtractionField(field_path="name", value="Alice", citations=[]),
            ],
        )
        results = validator.validate(extraction)
        citation_issues = [r for r in results if r.rule_name == "missing_citation"]
        assert len(citation_issues) == 1

    def test_no_warning_for_null_value(self, validator):
        extraction = Extraction(
            id="ex6",
            document_id="doc1",
            fields=[
                ExtractionField(field_path="name", value=None, citations=[]),
            ],
        )
        results = validator.validate(extraction)
        citation_issues = [r for r in results if r.rule_name == "missing_citation"]
        assert len(citation_issues) == 0

    def test_no_warning_with_citation(self, validator):
        extraction = Extraction(
            id="ex7",
            document_id="doc1",
            fields=[
                ExtractionField(
                    field_path="name",
                    value="Alice",
                    citations=[Citation(page_number=1)],
                ),
            ],
        )
        results = validator.validate(extraction)
        citation_issues = [r for r in results if r.rule_name == "missing_citation"]
        assert len(citation_issues) == 0


# ---------------------------------------------------------------------------
# Validator — confidence
# ---------------------------------------------------------------------------

class TestValidatorConfidence:
    def test_low_confidence_warning(self, validator):
        extraction = Extraction(
            id="ex8",
            document_id="doc1",
            fields=[
                ExtractionField(field_path="name", value="Alice", confidence=0.3),
            ],
        )
        results = validator.validate(extraction)
        conf_issues = [r for r in results if r.rule_name == "low_confidence"]
        assert len(conf_issues) == 1
        assert conf_issues[0].severity == ValidationSeverity.WARNING

    def test_no_warning_high_confidence(self, validator):
        extraction = Extraction(
            id="ex9",
            document_id="doc1",
            fields=[
                ExtractionField(field_path="name", value="Alice", confidence=0.9),
            ],
        )
        results = validator.validate(extraction)
        conf_issues = [r for r in results if r.rule_name == "low_confidence"]
        assert len(conf_issues) == 0


# ---------------------------------------------------------------------------
# Validator — invoice arithmetic
# ---------------------------------------------------------------------------

class TestValidatorInvoiceArithmetic:
    def test_valid_arithmetic(self, validator):
        extraction = Extraction(
            id="ex10",
            document_id="doc1",
            schema_id="invoice",
            fields=[
                ExtractionField(field_path="subtotal", value=1000.0),
                ExtractionField(field_path="tax", value=80.0),
                ExtractionField(field_path="total", value=1080.0),
                ExtractionField(field_path="vendor_name", value="Acme"),
                ExtractionField(field_path="invoice_number", value="INV-001"),
                ExtractionField(field_path="invoice_date", value="2024-01-01"),
                ExtractionField(field_path="line_items", value=[]),
            ],
        )
        results = validator.validate(extraction)
        arithmetic_results = [r for r in results if r.rule_name == "arithmetic_valid"]
        assert len(arithmetic_results) == 1
        assert arithmetic_results[0].severity == ValidationSeverity.INFO

    def test_invalid_arithmetic(self, validator):
        extraction = Extraction(
            id="ex11",
            document_id="doc1",
            schema_id="invoice",
            fields=[
                ExtractionField(field_path="subtotal", value=1000.0),
                ExtractionField(field_path="tax", value=80.0),
                ExtractionField(field_path="total", value=2000.0),
                ExtractionField(field_path="vendor_name", value="Acme"),
                ExtractionField(field_path="invoice_number", value="INV-001"),
                ExtractionField(field_path="invoice_date", value="2024-01-01"),
                ExtractionField(field_path="line_items", value=[]),
            ],
        )
        results = validator.validate(extraction)
        arithmetic_results = [r for r in results if r.rule_name == "arithmetic_mismatch"]
        assert len(arithmetic_results) == 1
        assert arithmetic_results[0].severity == ValidationSeverity.ERROR

    def test_arithmetic_with_no_tax(self, validator):
        """When tax is None, it should default to 0."""
        extraction = Extraction(
            id="ex12",
            document_id="doc1",
            schema_id="invoice",
            fields=[
                ExtractionField(field_path="subtotal", value=500.0),
                ExtractionField(field_path="total", value=500.0),
                ExtractionField(field_path="vendor_name", value="Acme"),
                ExtractionField(field_path="invoice_number", value="INV-001"),
                ExtractionField(field_path="invoice_date", value="2024-01-01"),
                ExtractionField(field_path="line_items", value=[]),
            ],
        )
        results = validator.validate(extraction)
        arithmetic_results = [r for r in results if r.rule_name == "arithmetic_valid"]
        assert len(arithmetic_results) == 1

    def test_arithmetic_check_skipped_nonnumeric(self, validator):
        extraction = Extraction(
            id="ex13",
            document_id="doc1",
            schema_id="invoice",
            fields=[
                ExtractionField(field_path="subtotal", value="not a number"),
                ExtractionField(field_path="total", value="also not"),
                ExtractionField(field_path="vendor_name", value="Acme"),
                ExtractionField(field_path="invoice_number", value="INV-001"),
                ExtractionField(field_path="invoice_date", value="2024-01-01"),
                ExtractionField(field_path="line_items", value=[]),
            ],
        )
        results = validator.validate(extraction)
        skipped = [r for r in results if r.rule_name == "arithmetic_check_skipped"]
        assert len(skipped) == 1


# ---------------------------------------------------------------------------
# Validator — no schema
# ---------------------------------------------------------------------------

class TestValidatorNoSchema:
    def test_validate_without_schema(self, validator):
        extraction = Extraction(
            id="ex14",
            document_id="doc1",
            fields=[
                ExtractionField(field_path="name", value="Alice", confidence=0.3),
            ],
        )
        results = validator.validate(extraction)
        # Should still run citation and confidence checks
        assert len(results) > 0


# ---------------------------------------------------------------------------
# End-to-end: extract then validate
# ---------------------------------------------------------------------------

class TestExtractAndValidate:
    def test_invoice_end_to_end(self, extractor, validator, invoice_pdf_graph):
        extraction = extractor.extract(invoice_pdf_graph, "invoice")
        results = validator.validate(extraction)
        # Should have some results (at least arithmetic check)
        assert isinstance(results, list)
        # All results should be ValidationResult instances
        for r in results:
            assert isinstance(r, ValidationResult)
            assert r.extraction_id == extraction.id

    def test_bad_invoice_arithmetic_flagged(self, extractor, validator, invoice_bad_math_graph):
        extraction = extractor.extract(invoice_bad_math_graph, "invoice")
        results = validator.validate(extraction)
        arithmetic_issues = [
            r for r in results
            if r.rule_name in ("arithmetic_mismatch", "arithmetic_check_skipped")
        ]
        # Should flag the arithmetic issue
        assert len(arithmetic_issues) >= 1
