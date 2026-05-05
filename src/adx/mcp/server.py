"""MCP server exposing ADX inspector tools."""

from __future__ import annotations

from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from adx.client import ADX


def create_mcp_server(storage_dir: str | None = None) -> Server:
    """Create an MCP server with ADX tools registered."""
    server = Server("adx")
    client = ADX(storage_dir=storage_dir)

    tool_defs = [
        Tool(
            name="adx_upload",
            description="Upload and process a document file. Returns file ID and metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to upload"},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="adx_profile",
            description="Profile a document: file type, page/sheet count, detected document types.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "ID of the uploaded file"},
                },
                "required": ["file_id"],
            },
        ),
        Tool(
            name="adx_structure",
            description="Get document structure: sections, tables, pages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "ID of the uploaded file"},
                },
                "required": ["file_id"],
            },
        ),
        Tool(
            name="adx_search",
            description="Search text and cells within a single document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "ID of the uploaded file"},
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Max results", "default": 20},
                },
                "required": ["file_id", "query"],
            },
        ),
        Tool(
            name="adx_search_corpus",
            description="Search across all uploaded documents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Max results", "default": 20},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="adx_get_page",
            description="Get text and tables from a specific page.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "ID of the uploaded file"},
                    "page_number": {"type": "integer", "description": "Page number (1-based)"},
                },
                "required": ["file_id", "page_number"],
            },
        ),
        Tool(
            name="adx_get_table",
            description="Get a specific table by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "ID of the uploaded file"},
                    "table_id": {"type": "string", "description": "Table ID"},
                },
                "required": ["file_id", "table_id"],
            },
        ),
        Tool(
            name="adx_to_markdown",
            description="Export a document as markdown.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "ID of the uploaded file"},
                },
                "required": ["file_id"],
            },
        ),
        Tool(
            name="adx_chunk",
            description="Chunk a document for retrieval pipelines.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "ID of the uploaded file"},
                    "strategy": {"type": "string", "default": "section_aware",
                                 "description": "Strategy: fixed_size, section_aware, table_only"},
                    "max_chunk_size": {"type": "integer", "default": 1000, "description": "Max tokens per chunk"},
                },
                "required": ["file_id"],
            },
        ),
        Tool(
            name="adx_list_sheets",
            description="List workbook sheets in a spreadsheet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "ID of the uploaded file"},
                },
                "required": ["file_id"],
            },
        ),
    ]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return tool_defs

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        import json

        handlers: dict[str, Any] = {
            "adx_upload": lambda args: _upload(client, args),
            "adx_profile": lambda args: client.profile(args["file_id"]),
            "adx_structure": lambda args: client.structure(args["file_id"]),
            "adx_search": lambda args: client.search(
                args["file_id"], args["query"], args.get("max_results", 20)
            ),
            "adx_search_corpus": lambda args: client.search_corpus(
                args["query"], max_results=args.get("max_results", 20)
            ),
            "adx_get_page": lambda args: client.get_page(args["file_id"], args["page_number"]),
            "adx_get_table": lambda args: client.get_table(args["file_id"], args["table_id"]),
            "adx_to_markdown": lambda args: client.to_markdown(args["file_id"]),
            "adx_chunk": lambda args: _chunk(client, args),
            "adx_list_sheets": lambda args: client.list_sheets(args["file_id"]),
        }

        handler = handlers.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        try:
            result = handler(arguments)
            if isinstance(result, str):
                text = result
            else:
                text = json.dumps(result, indent=2, default=str)
            return [TextContent(type="text", text=text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]

    return server


def _upload(client: ADX, args: dict[str, Any]) -> dict[str, Any]:
    graph = client.upload(args["file_path"])
    return {
        "file_id": graph.document.id,
        "filename": graph.document.filename,
        "file_type": graph.document.file_type.value,
        "page_count": graph.document.page_count,
        "sheet_count": graph.document.sheet_count,
    }


def _chunk(client: ADX, args: dict[str, Any]) -> dict[str, Any]:
    chunks = client.chunk(
        args["file_id"],
        strategy=args.get("strategy", "section_aware"),
        max_chunk_size=args.get("max_chunk_size", 1000),
    )
    return {
        "chunk_count": len(chunks),
        "chunks": [
            {
                "id": c.id,
                "text": c.text[:500],
                "chunk_type": c.chunk_type,
                "section_path": c.section_path,
                "page_numbers": c.page_numbers,
                "token_count": c.token_count,
            }
            for c in chunks
        ],
    }
