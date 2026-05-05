"""Tests for custom extraction schemas (register_spec and data_table)."""

from __future__ import annotations

import pytest

from adx.client import ADX
from adx.extraction.extractor import Extractor
from adx.extraction.schemas import (
    DATA_TABLE_SCHEMA,
    REGISTER_SPEC_SCHEMA,
    SchemaRegistry,
)
from adx.models.document import (
    Document,
    DocumentGraph,
    FileType,
    Page,
    Table,
    TableCell,
    TextBlock,
    TextBlockType,
)


class TestRegisterSpecSchema:
    def test_schema_structure(self):
        assert REGISTER_SPEC_SCHEMA.id == "register_spec"
        fields = {f.name for f in REGISTER_SPEC_SCHEMA.fields}
        assert "register_name" in fields
        assert "base_address" in fields
        assert "bit_fields" in fields

    def test_json_schema_output(self):
        js = REGISTER_SPEC_SCHEMA.to_json_schema()
        assert "properties" in js
        assert "register_name" in js["properties"]
        assert "base_address" in js["properties"]

    def test_registered_in_registry(self):
        reg = SchemaRegistry()
        schema = reg.get("register_spec")
        assert schema is not None
        assert schema.id == "register_spec"


class TestDataTableSchema:
    def test_schema_structure(self):
        assert DATA_TABLE_SCHEMA.id == "data_table"
        fields = {f.name for f in DATA_TABLE_SCHEMA.fields}
        assert "columns" in fields
        assert "rows" in fields
        assert "row_count" in fields

    def test_json_schema_output(self):
        js = DATA_TABLE_SCHEMA.to_json_schema()
        assert "properties" in js
        assert "columns" in js["properties"]

    def test_registered_in_registry(self):
        reg = SchemaRegistry()
        schema = reg.get("data_table")
        assert schema is not None


class TestRegisterSpecExtraction:
    def _graph_with_register_text(self, text, table=None):
        page = Page(
            page_number=1,
            text_blocks=[
                TextBlock(text=text, block_type=TextBlockType.PARAGRAPH, reading_order_index=0),
            ],
            tables=[table] if table else [],
        )
        return DocumentGraph(
            document=Document(filename="reg.pdf", file_type=FileType.PDF),
            pages=[page],
        )

    def test_extracts_register_name(self):
        graph = self._graph_with_register_text("Register: CTRL_REG\nAddress: 0x1000")
        ext = Extractor()
        result = ext.extract(graph, "register_spec")
        assert result.output.get("register_name") == "CTRL_REG"

    def test_extracts_base_address(self):
        graph = self._graph_with_register_text("Register: TEST\nBase Address: 0xDEAD")
        ext = Extractor()
        result = ext.extract(graph, "register_spec")
        assert result.output.get("base_address") == "0xDEAD"

    def test_extracts_width(self):
        graph = self._graph_with_register_text("Register: X\nAddress: 0x00\nWidth: 32")
        ext = Extractor()
        result = ext.extract(graph, "register_spec")
        assert result.output.get("register_width") == 32

    def test_extracts_description(self):
        graph = self._graph_with_register_text(
            "Register: X\nAddress: 0x00\nDescription: Controls the main clock"
        )
        ext = Extractor()
        result = ext.extract(graph, "register_spec")
        assert "main clock" in result.output.get("description", "")

    def test_extracts_bit_fields_from_table(self):
        table = Table(
            row_count=3, column_count=3,
            cells=[
                TableCell(row_index=0, column_index=0, value="Bits"),
                TableCell(row_index=0, column_index=1, value="Name"),
                TableCell(row_index=0, column_index=2, value="Description"),
                TableCell(row_index=1, column_index=0, value="31:16"),
                TableCell(row_index=1, column_index=1, value="RESERVED"),
                TableCell(row_index=1, column_index=2, value="Reserved"),
                TableCell(row_index=2, column_index=0, value="15:0"),
                TableCell(row_index=2, column_index=1, value="DATA"),
                TableCell(row_index=2, column_index=2, value="Data field"),
            ],
        )
        graph = self._graph_with_register_text("Register: REG1\nAddress: 0x00", table)
        ext = Extractor()
        result = ext.extract(graph, "register_spec")
        bit_fields = result.output.get("bit_fields", [])
        assert len(bit_fields) == 2
        assert bit_fields[0].get("bits") == "31:16"

    def test_missing_fields_warns(self):
        graph = self._graph_with_register_text("Some text without any relevant patterns")
        ext = Extractor()
        result = ext.extract(graph, "register_spec")
        # At least some fields should have warnings or low confidence
        low_conf_fields = [f for f in result.fields if f.confidence == 0.0]
        assert len(low_conf_fields) > 0


class TestDataTableExtraction:
    def _graph_with_table(self, headers, data, file_type=FileType.PDF):
        cells = []
        for i, h in enumerate(headers):
            cells.append(TableCell(row_index=0, column_index=i, value=h))
        for r_idx, row in enumerate(data):
            for c_idx, val in enumerate(row):
                cells.append(TableCell(row_index=r_idx + 1, column_index=c_idx, value=val))
        table = Table(
            row_count=len(data) + 1,
            column_count=len(headers),
            cells=cells,
            page_number=1,
        )
        page = Page(page_number=1, tables=[table])
        return DocumentGraph(
            document=Document(filename="data.pdf", file_type=file_type),
            pages=[page],
        )

    def test_extracts_columns(self):
        graph = self._graph_with_table(["Name", "Age"], [["Alice", "30"], ["Bob", "25"]])
        ext = Extractor()
        result = ext.extract(graph, "data_table")
        columns = result.output.get("columns", [])
        assert len(columns) == 2
        assert columns[0]["name"] == "Name"

    def test_infers_number_type(self):
        graph = self._graph_with_table(["Value"], [["1.5"], ["2.3"], ["3.7"]])
        ext = Extractor()
        result = ext.extract(graph, "data_table")
        columns = result.output.get("columns", [])
        assert columns[0]["type"] == "number"

    def test_infers_integer_type(self):
        graph = self._graph_with_table(["Count"], [["1"], ["2"], ["3"]])
        ext = Extractor()
        result = ext.extract(graph, "data_table")
        columns = result.output.get("columns", [])
        assert columns[0]["type"] == "integer"

    def test_infers_date_type(self):
        graph = self._graph_with_table(["Date"], [["2024-01-01"], ["2024-02-01"]])
        ext = Extractor()
        result = ext.extract(graph, "data_table")
        columns = result.output.get("columns", [])
        assert columns[0]["type"] == "date"

    def test_infers_string_type(self):
        graph = self._graph_with_table(["City"], [["NYC"], ["London"]])
        ext = Extractor()
        result = ext.extract(graph, "data_table")
        columns = result.output.get("columns", [])
        assert columns[0]["type"] == "string"

    def test_extracts_row_count(self):
        graph = self._graph_with_table(["X"], [["a"], ["b"], ["c"]])
        ext = Extractor()
        result = ext.extract(graph, "data_table")
        assert result.output.get("row_count") == 3

    def test_extracts_rows(self):
        graph = self._graph_with_table(["A", "B"], [["1", "2"], ["3", "4"]])
        ext = Extractor()
        result = ext.extract(graph, "data_table")
        rows = result.output.get("rows", [])
        assert len(rows) == 2
        assert rows[0] == ["1", "2"]

    def test_no_tables_warns(self):
        page = Page(page_number=1)
        graph = DocumentGraph(
            document=Document(filename="empty.pdf", file_type=FileType.PDF),
            pages=[page],
        )
        ext = Extractor()
        result = ext.extract(graph, "data_table")
        warnings = [w for f in result.fields for w in f.warnings]
        assert any("No tables" in w for w in warnings)

    def test_has_citations(self):
        graph = self._graph_with_table(["X"], [["v"]])
        ext = Extractor()
        result = ext.extract(graph, "data_table")
        all_citations = [c for f in result.fields for c in f.citations]
        assert len(all_citations) > 0
