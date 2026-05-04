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


@cli.command()
def serve() -> None:
    """Start the ADX API server."""
    import uvicorn
    uvicorn.run("adx.api.app:app", host="0.0.0.0", port=8000, reload=True)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
