---
title: MCP Tools
---

# MCP Tools

DocuNav tools are designed to be exposed as MCP (Model Context Protocol) tools, making them available to any MCP-compatible AI agent.

## Planned MCP Tools

| Tool | Description |
|---|---|
| `docunav.profile` | Profile a document — metadata, type, recommended tools |
| `docunav.structure` | List sections, tables, and page outline |
| `docunav.search` | Full-text search with citations |
| `docunav.get_page` | Read a specific page's content |
| `docunav.get_table` | Read a specific table |
| `docunav.list_sheets` | List spreadsheet sheets |
| `docunav.read_range` | Read a cell range |
| `docunav.find_cells` | Search cells by value |
| `docunav.inspect_formula` | Trace formula dependencies |
| `docunav.extract` | Extract fields with a schema |
| `docunav.validate` | Validate an extraction |

## MCP Server Configuration

MCP server support is planned for a future release. The MCP tools will wrap the same core functions as the REST API and Python SDK.

Example future configuration:

```json
{
  "mcpServers": {
    "docunav": {
      "command": "docunav",
      "args": ["mcp"]
    }
  }
}
```

## Current Alternatives

Until MCP support ships, agents can use:

- **Python SDK** — direct function calls via `from docunav import DocuNav`
- **REST API** — HTTP endpoints via `docunav serve`
- **CLI** — shell commands for scripting
