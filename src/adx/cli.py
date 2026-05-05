"""ADX CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table as RichTable
from rich.panel import Panel
from rich.json import JSON as RichJSON

from adx.client import ADX

console = Console()


def _client(storage_dir: str | None = None) -> ADX:
    return ADX(storage_dir=storage_dir)


@click.group()
@click.option("--storage-dir", default=None, help="Storage directory path.")
@click.pass_context
def cli(ctx: click.Context, storage_dir: str | None) -> None:
    """ADX — Agent-native document intelligence layer."""
    ctx.ensure_object(dict)
    ctx.obj["storage_dir"] = storage_dir


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_context
def upload(ctx: click.Context, file_path: str) -> None:
    """Upload and process a file."""
    client = _client(ctx.obj.get("storage_dir"))
    with console.status("Processing..."):
        graph = client.upload(file_path)
    console.print(f"[green]Uploaded:[/green] {graph.document.filename}")
    console.print(f"[green]File ID:[/green]  {graph.document.id}")
    console.print(f"[green]Type:[/green]     {graph.document.file_type.value}")
    console.print(f"[green]Pages:[/green]    {graph.document.page_count}")
    console.print(f"[green]Sheets:[/green]   {graph.document.sheet_count}")
    console.print(f"[green]Status:[/green]   {graph.document.processing_status.value}")


@cli.command()
@click.pass_context
def files(ctx: click.Context) -> None:
    """List all processed files."""
    client = _client(ctx.obj.get("storage_dir"))
    ids = client.list_files()
    if not ids:
        console.print("[dim]No files found.[/dim]")
        return
    table = RichTable(title="Processed Files")
    table.add_column("File ID")
    table.add_column("Filename")
    table.add_column("Type")
    table.add_column("Status")
    for fid in ids:
        graph = client.get_graph(fid)
        if graph:
            table.add_row(
                graph.document.id,
                graph.document.filename,
                graph.document.file_type.value,
                graph.document.processing_status.value,
            )
    console.print(table)


@cli.command()
@click.argument("file_id")
@click.pass_context
def profile(ctx: click.Context, file_id: str) -> None:
    """Profile a document."""
    client = _client(ctx.obj.get("storage_dir"))
    result = client.profile(file_id)
    console.print(Panel(RichJSON(json.dumps(result, indent=2, default=str)), title="Document Profile"))


@cli.command()
@click.argument("file_id")
@click.pass_context
def structure(ctx: click.Context, file_id: str) -> None:
    """Show document structure."""
    client = _client(ctx.obj.get("storage_dir"))
    result = client.structure(file_id)
    console.print(Panel(RichJSON(json.dumps(result, indent=2, default=str)), title="Document Structure"))


@cli.command()
@click.argument("file_id")
@click.argument("query")
@click.pass_context
def search(ctx: click.Context, file_id: str, query: str) -> None:
    """Search document content."""
    client = _client(ctx.obj.get("storage_dir"))
    result = client.search(file_id, query)

    if result.get("text_matches"):
        console.print(f"\n[bold]Text Matches ({len(result['text_matches'])}):[/bold]")
        for m in result["text_matches"]:
            console.print(f"  [cyan]Page {m['page_number']}:[/cyan] {m['text'][:120]}...")

    if result.get("cell_matches"):
        console.print(f"\n[bold]Cell Matches ({len(result['cell_matches'])}):[/bold]")
        for m in result["cell_matches"]:
            console.print(f"  [cyan]{m['sheet_name']}!{m['address']}:[/cyan] {m['value']}")


@cli.command()
@click.argument("file_id")
@click.option("--schema", "-s", default=None, help="Schema name (invoice, contract, financial_model, table)")
@click.pass_context
def extract(ctx: click.Context, file_id: str, schema: str | None) -> None:
    """Extract structured data from a document."""
    client = _client(ctx.obj.get("storage_dir"))
    with console.status("Extracting..."):
        extraction = client.extract(file_id, schema=schema)

    console.print(f"[green]Extraction ID:[/green] {extraction.id}")
    console.print(f"[green]Schema:[/green]        {extraction.schema_name}")
    console.print(f"[green]Confidence:[/green]    {extraction.confidence:.2f}")
    console.print()

    table = RichTable(title="Extracted Fields")
    table.add_column("Field")
    table.add_column("Value")
    table.add_column("Confidence")
    table.add_column("Citation")
    table.add_column("Warnings")

    for field in extraction.fields:
        value_str = str(field.value)[:80] if field.value is not None else "[dim]—[/dim]"
        citations_str = "; ".join(c.to_short_ref() for c in field.citations) or "[dim]none[/dim]"
        warnings_str = "; ".join(field.warnings) if field.warnings else ""
        conf_color = "green" if field.confidence > 0.8 else "yellow" if field.confidence > 0.5 else "red"
        table.add_row(
            field.field_path,
            value_str,
            f"[{conf_color}]{field.confidence:.2f}[/{conf_color}]",
            citations_str,
            warnings_str,
        )

    console.print(table)


@cli.command()
@click.argument("extraction_id")
@click.pass_context
def validate(ctx: click.Context, extraction_id: str) -> None:
    """Validate an extraction result."""
    client = _client(ctx.obj.get("storage_dir"))
    results = client.validate(extraction_id)

    if not results:
        console.print("[green]No validation issues found.[/green]")
        return

    table = RichTable(title="Validation Results")
    table.add_column("Severity")
    table.add_column("Rule")
    table.add_column("Message")
    table.add_column("Fields")

    for r in results:
        sev_color = {"error": "red", "warning": "yellow", "info": "blue"}.get(r.severity.value, "white")
        table.add_row(
            f"[{sev_color}]{r.severity.value}[/{sev_color}]",
            r.rule_name,
            r.message,
            ", ".join(r.affected_fields),
        )

    console.print(table)
    passed = all(r.severity.value != "error" for r in results)
    if passed:
        console.print("[green]Validation passed (with warnings).[/green]")
    else:
        console.print("[red]Validation failed.[/red]")


@cli.command(name="export")
@click.argument("extraction_id")
@click.option("--format", "-f", "fmt", default="json", help="Output format (json, markdown, csv)")
@click.pass_context
def export_cmd(ctx: click.Context, extraction_id: str, fmt: str) -> None:
    """Export extraction results."""
    client = _client(ctx.obj.get("storage_dir"))
    result = client.export(extraction_id, fmt)
    console.print(result)


@cli.command()
@click.argument("file_id")
@click.pass_context
def sheets(ctx: click.Context, file_id: str) -> None:
    """List workbook sheets."""
    client = _client(ctx.obj.get("storage_dir"))
    result = client.list_sheets(file_id)

    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
        return

    table = RichTable(title="Sheets")
    table.add_column("Name")
    table.add_column("Visible")
    table.add_column("Used Range")
    table.add_column("Formulas")
    table.add_column("Hidden Rows")
    table.add_column("Hidden Cols")

    for s in result.get("sheets", []):
        table.add_row(
            s["name"],
            "[green]yes[/green]" if s["visible"] else "[red]no[/red]",
            s.get("used_range", ""),
            str(s.get("formula_count", 0)),
            str(s.get("hidden_row_count", 0)),
            str(s.get("hidden_column_count", 0)),
        )

    console.print(table)


@cli.command(name="upload-dir")
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("--recursive/--no-recursive", default=True, help="Recurse into subdirectories.")
@click.pass_context
def upload_dir(ctx: click.Context, directory: str, recursive: bool) -> None:
    """Upload all supported files in a directory."""
    client = _client(ctx.obj.get("storage_dir"))
    with console.status("Processing directory..."):
        result = client.upload_directory(directory, recursive=recursive)

    console.print(f"[green]Total:[/green]      {result.total_files}")
    console.print(f"[green]Successful:[/green] {result.successful}")
    if result.failed:
        console.print(f"[red]Failed:[/red]     {result.failed}")
        for path, error in result.errors.items():
            console.print(f"  [red]{path}:[/red] {error}")

    if result.graphs:
        table = RichTable(title="Uploaded Files")
        table.add_column("File ID")
        for fid in result.graphs:
            graph = client.get_graph(fid)
            if graph:
                table.add_row(f"{graph.document.id} ({graph.document.filename})")
        console.print(table)


@cli.command(name="search-all")
@click.argument("query")
@click.option("--max-results", default=20, help="Maximum results to return.")
@click.pass_context
def search_all(ctx: click.Context, query: str, max_results: int) -> None:
    """Search across all uploaded documents."""
    client = _client(ctx.obj.get("storage_dir"))
    hits = client.search_corpus(query, max_results=max_results)

    if not hits:
        console.print("[dim]No matches found.[/dim]")
        return

    table = RichTable(title=f"Corpus Search: '{query}'")
    table.add_column("Score", justify="right")
    table.add_column("File")
    table.add_column("Location")
    table.add_column("Snippet")

    for hit in hits:
        table.add_row(
            str(hit["score"]),
            hit["filename"],
            hit["citation"],
            hit["text_snippet"][:80],
        )

    console.print(table)
    console.print(f"\n[dim]{len(hits)} results[/dim]")


@cli.command()
@click.argument("file_id")
@click.option("--strategy", "-s", default="section_aware", help="Chunking strategy.")
@click.option("--max-size", default=1000, help="Max tokens per chunk.")
@click.pass_context
def chunk(ctx: click.Context, file_id: str, strategy: str, max_size: int) -> None:
    """Chunk a document for retrieval."""
    client = _client(ctx.obj.get("storage_dir"))
    try:
        chunks = client.chunk(file_id, strategy=strategy, max_chunk_size=max_size)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    console.print(f"[green]{len(chunks)} chunks generated[/green]\n")
    for i, c in enumerate(chunks, 1):
        loc = ", ".join(f"p{p}" for p in c.page_numbers) if c.page_numbers else c.sheet_name or "—"
        console.print(f"[bold]Chunk {i}[/bold] ({c.chunk_type}, ~{c.token_count} tokens, {loc})")
        console.print(f"  {c.text[:120]}{'...' if len(c.text) > 120 else ''}")
        if c.section_path:
            console.print(f"  [dim]Section: {' > '.join(c.section_path)}[/dim]")
        console.print()


@cli.command()
@click.argument("file_id")
@click.pass_context
def markdown(ctx: click.Context, file_id: str) -> None:
    """Export document as markdown."""
    client = _client(ctx.obj.get("storage_dir"))
    try:
        md = client.to_markdown(file_id)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    console.print(md)


@cli.command()
def serve() -> None:
    """Start the ADX API server."""
    import uvicorn
    uvicorn.run("adx.api.app:app", host="0.0.0.0", port=8000, reload=True)


@cli.command()
@click.option("--storage-dir", default=None, help="Storage directory for MCP server.")
def mcp(storage_dir: str | None) -> None:
    """Start the MCP server (stdio transport)."""
    try:
        from adx.mcp import create_mcp_server
    except ImportError:
        console.print("[red]MCP SDK not installed. Run: pip install 'adx[mcp]'[/red]")
        sys.exit(1)

    import asyncio
    from mcp.server.stdio import stdio_server

    server = create_mcp_server(storage_dir)

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
