"""Tests for MCP tool wrappers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp.types import ListToolsRequest, CallToolRequest

from adx.mcp.server import create_mcp_server


@pytest.fixture
def server(tmp_path):
    return create_mcp_server(str(tmp_path / "store"))


@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "test.csv"
    p.write_text("name,value\nfoo,1\nbar,2\n")
    return p


async def _list_tools(server):
    handler = server.request_handlers[ListToolsRequest]
    result = await handler(ListToolsRequest(method="tools/list"))
    # Result may be wrapped in ServerResult
    if hasattr(result, 'root'):
        result = result.root
    return result.tools


async def _call_tool(server, name, arguments):
    handler = server.request_handlers[CallToolRequest]
    result = await handler(CallToolRequest(
        method="tools/call",
        params={"name": name, "arguments": arguments},
    ))
    if hasattr(result, 'root'):
        result = result.root
    return result.content


class TestMcpToolRegistration:
    async def test_list_tools_returns_tools(self, server):
        tools = await _list_tools(server)
        assert len(tools) >= 8

    async def test_tool_names(self, server):
        tools = await _list_tools(server)
        names = {t.name for t in tools}
        expected = {
            "adx_upload", "adx_profile", "adx_structure", "adx_search",
            "adx_search_corpus", "adx_get_page", "adx_get_table",
            "adx_to_markdown", "adx_chunk", "adx_list_sheets",
        }
        assert expected.issubset(names)

    async def test_tools_have_schemas(self, server):
        tools = await _list_tools(server)
        for tool in tools:
            assert tool.inputSchema is not None
            assert "properties" in tool.inputSchema

    async def test_tools_have_descriptions(self, server):
        tools = await _list_tools(server)
        for tool in tools:
            assert tool.description
            assert len(tool.description) > 10


class TestMcpToolExecution:
    async def test_upload(self, server, csv_path):
        result = await _call_tool(server, "adx_upload", {"file_path": str(csv_path)})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "file_id" in data
        assert data["filename"] == "test.csv"

    async def test_profile(self, server, csv_path):
        upload_result = await _call_tool(server, "adx_upload", {"file_path": str(csv_path)})
        file_id = json.loads(upload_result[0].text)["file_id"]

        result = await _call_tool(server, "adx_profile", {"file_id": file_id})
        data = json.loads(result[0].text)
        assert "filename" in data

    async def test_search_corpus(self, server, csv_path):
        await _call_tool(server, "adx_upload", {"file_path": str(csv_path)})
        result = await _call_tool(server, "adx_search_corpus", {"query": "foo"})
        data = json.loads(result[0].text)
        assert isinstance(data, list)

    async def test_to_markdown(self, server, csv_path):
        upload_result = await _call_tool(server, "adx_upload", {"file_path": str(csv_path)})
        file_id = json.loads(upload_result[0].text)["file_id"]

        result = await _call_tool(server, "adx_to_markdown", {"file_id": file_id})
        assert isinstance(result[0].text, str)
        assert len(result[0].text) > 0

    async def test_chunk(self, server, csv_path):
        upload_result = await _call_tool(server, "adx_upload", {"file_path": str(csv_path)})
        file_id = json.loads(upload_result[0].text)["file_id"]

        result = await _call_tool(server, "adx_chunk", {"file_id": file_id})
        data = json.loads(result[0].text)
        assert "chunk_count" in data
        assert data["chunk_count"] > 0

    async def test_unknown_tool(self, server):
        result = await _call_tool(server, "nonexistent_tool", {})
        assert "Unknown tool" in result[0].text

    async def test_error_handling(self, server):
        result = await _call_tool(server, "adx_profile", {"file_id": "nonexistent"})
        assert "Error" in result[0].text

    async def test_search_single_document(self, server, csv_path):
        upload_result = await _call_tool(server, "adx_upload", {"file_path": str(csv_path)})
        file_id = json.loads(upload_result[0].text)["file_id"]

        result = await _call_tool(server, "adx_search", {
            "file_id": file_id,
            "query": "foo",
        })
        data = json.loads(result[0].text)
        assert isinstance(data, dict)
