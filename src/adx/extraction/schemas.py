"""Built-in extraction schemas and schema registry."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FieldDef(BaseModel):
    name: str
    description: str = ""
    field_type: str = "string"
    required: bool = True
    validation_rules: list[str] = Field(default_factory=list)


class ExtractionSchema(BaseModel):
    id: str
    name: str
    description: str = ""
    version: str = "1.0"
    fields: list[FieldDef] = Field(default_factory=list)

    def to_json_schema(self) -> dict[str, Any]:
        """Convert to JSON Schema for LLM-based extraction."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        type_map = {
            "string": "string",
            "number": "number",
            "integer": "integer",
            "boolean": "boolean",
            "date": "string",
            "currency": "number",
            "array": "array",
            "object": "object",
        }

        for field_def in self.fields:
            prop: dict[str, Any] = {
                "type": type_map.get(field_def.field_type, "string"),
                "description": field_def.description,
            }
            if field_def.field_type == "date":
                prop["format"] = "date"
            if field_def.field_type == "array":
                prop["items"] = {"type": "object"}
            properties[field_def.name] = prop
            if field_def.required:
                required.append(field_def.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


# ---------------------------------------------------------------------------
# Built-in schemas
# ---------------------------------------------------------------------------

INVOICE_SCHEMA = ExtractionSchema(
    id="invoice",
    name="Invoice",
    description="Standard invoice extraction schema.",
    fields=[
        FieldDef(name="vendor_name", description="Name of the vendor/supplier"),
        FieldDef(name="vendor_address", description="Address of the vendor", required=False),
        FieldDef(name="invoice_number", description="Invoice number/ID"),
        FieldDef(name="invoice_date", description="Date of the invoice", field_type="date"),
        FieldDef(name="due_date", description="Payment due date", field_type="date", required=False),
        FieldDef(name="purchase_order", description="PO number", required=False),
        FieldDef(
            name="line_items",
            description="List of line items with description, quantity, unit_price, and amount",
            field_type="array",
        ),
        FieldDef(name="subtotal", description="Subtotal before tax", field_type="currency"),
        FieldDef(name="tax", description="Tax amount", field_type="currency", required=False),
        FieldDef(name="total", description="Total amount due", field_type="currency",
                 validation_rules=["total_should_equal_subtotal_plus_tax"]),
        FieldDef(name="currency", description="Currency code (e.g. USD, EUR)", required=False),
        FieldDef(name="payment_terms", description="Payment terms", required=False),
    ],
)

CONTRACT_SCHEMA = ExtractionSchema(
    id="contract",
    name="Contract Summary",
    description="Key contract terms extraction schema.",
    fields=[
        FieldDef(name="parties", description="Parties to the contract", field_type="array"),
        FieldDef(name="effective_date", description="Contract effective date", field_type="date"),
        FieldDef(name="termination_clause", description="Termination rights and conditions"),
        FieldDef(name="renewal_terms", description="Auto-renewal terms", required=False),
        FieldDef(name="governing_law", description="Governing law/jurisdiction"),
        FieldDef(name="payment_terms", description="Payment terms and schedule", required=False),
        FieldDef(name="obligations", description="Key obligations of each party", field_type="array"),
        FieldDef(name="liability_limit", description="Liability cap or limitation", required=False),
        FieldDef(name="confidentiality_clause", description="Confidentiality terms", required=False),
        FieldDef(name="notice_address", description="Address for legal notices", required=False),
    ],
)

FINANCIAL_MODEL_SCHEMA = ExtractionSchema(
    id="financial_model",
    name="Financial Model Summary",
    description="Key financial model assumptions and outputs.",
    fields=[
        FieldDef(name="workbook_summary", description="Brief description of the model"),
        FieldDef(name="key_sheets", description="Most important sheets", field_type="array"),
        FieldDef(name="assumption_cells", description="Key assumption inputs with cell refs", field_type="array"),
        FieldDef(name="revenue_drivers", description="Revenue drivers with cell refs", field_type="array"),
        FieldDef(name="cost_drivers", description="Cost drivers with cell refs", field_type="array", required=False),
        FieldDef(name="output_metrics", description="Key output metrics (EBITDA, NPV, etc.)", field_type="array"),
        FieldDef(name="hidden_sheet_warnings", description="Issues with hidden sheets", field_type="array", required=False),
    ],
)

TABLE_SCHEMA = ExtractionSchema(
    id="table",
    name="Generic Table",
    description="Extract tabular data as structured records.",
    fields=[
        FieldDef(name="headers", description="Column headers", field_type="array"),
        FieldDef(name="rows", description="Data rows", field_type="array"),
        FieldDef(name="row_count", description="Number of data rows", field_type="integer"),
    ],
)


REGISTER_SPEC_SCHEMA = ExtractionSchema(
    id="register_spec",
    name="Register Specification",
    description="Hardware register specification extraction.",
    fields=[
        FieldDef(name="register_name", description="Name of the register"),
        FieldDef(name="base_address", description="Base address (hex string)"),
        FieldDef(name="register_width", description="Register width in bits", field_type="integer", required=False),
        FieldDef(name="description", description="Register description", required=False),
        FieldDef(
            name="bit_fields",
            description="Bit field definitions with name, bits, access, reset value, and description",
            field_type="array",
        ),
    ],
)

DATA_TABLE_SCHEMA = ExtractionSchema(
    id="data_table",
    name="Data Table",
    description="Structured data table extraction with column type inference.",
    fields=[
        FieldDef(name="table_name", description="Name or title of the table", required=False),
        FieldDef(
            name="columns",
            description="Column definitions with name and inferred type",
            field_type="array",
        ),
        FieldDef(name="rows", description="Data rows", field_type="array"),
        FieldDef(name="row_count", description="Number of data rows", field_type="integer"),
    ],
)


class SchemaRegistry:
    """Registry of extraction schemas."""

    def __init__(self) -> None:
        self._schemas: dict[str, ExtractionSchema] = {
            "invoice": INVOICE_SCHEMA,
            "contract": CONTRACT_SCHEMA,
            "financial_model": FINANCIAL_MODEL_SCHEMA,
            "table": TABLE_SCHEMA,
            "register_spec": REGISTER_SPEC_SCHEMA,
            "data_table": DATA_TABLE_SCHEMA,
        }

    def get(self, schema_id: str) -> ExtractionSchema | None:
        return self._schemas.get(schema_id)

    def register(self, schema: ExtractionSchema) -> None:
        self._schemas[schema.id] = schema

    def list_schemas(self) -> list[dict[str, str]]:
        return [
            {"id": s.id, "name": s.name, "description": s.description}
            for s in self._schemas.values()
        ]

    def from_json_schema(self, schema_id: str, name: str, json_schema: dict[str, Any]) -> ExtractionSchema:
        """Create an ExtractionSchema from a JSON Schema dict."""
        fields: list[FieldDef] = []
        properties = json_schema.get("properties", {})
        required = json_schema.get("required", [])

        type_rmap = {
            "string": "string",
            "number": "number",
            "integer": "integer",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
        }

        for field_name, prop in properties.items():
            json_type = prop.get("type", "string")
            field_type = type_rmap.get(json_type, "string")
            if prop.get("format") == "date":
                field_type = "date"

            fields.append(FieldDef(
                name=field_name,
                description=prop.get("description", ""),
                field_type=field_type,
                required=field_name in required,
            ))

        schema = ExtractionSchema(
            id=schema_id,
            name=name,
            fields=fields,
        )
        self.register(schema)
        return schema
