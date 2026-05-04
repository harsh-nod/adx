---
title: MCP Tools
---

# MCP Tools

ADX tools are designed to be exposed as MCP (Model Context Protocol) tools, making them available to any MCP-compatible AI agent.

## Planned MCP Tools

| Tool | Description |
|---|---|
| `adx.profile` | Profile a document — metadata, type, recommended tools |
| `adx.structure` | List sections, tables, and page outline |
| `adx.search` | Full-text search with citations |
| `adx.get_page` | Read a specific page's content |
| `adx.get_table` | Read a specific table |
| `adx.list_sheets` | List spreadsheet sheets |
| `adx.read_range` | Read a cell range |
| `adx.find_cells` | Search cells by value |
| `adx.inspect_formula` | Trace formula dependencies |
| `adx.extract` | Extract fields with a schema |
| `adx.validate` | Validate an extraction |

## MCP Server Configuration

MCP server support is planned for a future release. The MCP tools will wrap the same core functions as the REST API and Python SDK.

Example future configuration:

```json
{
  "mcpServers": {
    "adx": {
      "command": "adx",
      "args": ["mcp"]
    }
  }
}
```

## Current Alternatives

Until MCP support ships, agents can use:

- **Python SDK** — direct function calls via `from adx import ADX`
- **REST API** — HTTP endpoints via `adx serve`
- **CLI** — shell commands for scripting
