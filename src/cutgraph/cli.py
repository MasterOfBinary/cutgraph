from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .media import ProbeError, probe_asset
from .mcp_server import create_server
from .render import RenderPlanError, plan_render
from .render_jobs import RenderExecutionError, run_render
from .store import load_project, save_project


app = typer.Typer(help="CutGraph non-destructive video project tools.")
console = Console()


@app.callback()
def root() -> None:
    """CutGraph command group."""


@app.command()
def validate(project_root: Path) -> None:
    """Validate a CutGraph project."""
    try:
        load_project(project_root)
    except ValueError as exc:
        console.print(f"Invalid CutGraph project: {exc}", style="red")
        raise typer.Exit(1) from exc

    console.print("CutGraph project is valid.", style="green")


@app.command()
def probe(project_root: Path, media_path: str) -> None:
    """Probe media with ffprobe and register it as a CutGraph asset."""
    try:
        project = load_project(project_root)
        asset = probe_asset(project, project_root, media_path)
        save_project(project_root, project)
    except (ProbeError, ValueError) as exc:
        console.print(f"Probe failed: {exc}", style="red")
        raise typer.Exit(1) from exc

    console.print(f"Registered asset {asset.id!r}.", style="green")


@app.command()
def dry_run(
    project_root: Path,
    timeline_id: str,
    output_path: str,
    preset: str = "final",
) -> None:
    """Compile a render plan without running FFmpeg."""
    try:
        project = load_project(project_root)
        plan = plan_render(project, project_root, timeline_id, output_path, preset=preset)
    except (RenderPlanError, ValueError) as exc:
        console.print(f"Dry run failed: {exc}", style="red")
        raise typer.Exit(1) from exc

    typer.echo(plan.model_dump_json(indent=2))


@app.command()
def render(
    project_root: Path,
    timeline_id: str,
    output_path: str,
    preset: str = "final",
) -> None:
    """Render a timeline with FFmpeg."""
    project = None
    try:
        project = load_project(project_root)
        record = run_render(project, project_root, timeline_id, output_path, preset=preset)
        save_project(project_root, project)
    except (RenderPlanError, RenderExecutionError, ValueError) as exc:
        if project is not None:
            save_project(project_root, project)
        console.print(f"Render failed: {exc}", style="red")
        raise typer.Exit(1) from exc

    console.print(f"Render {record.id!r} completed.", style="green")


@app.command()
def mcp(transport: str = "stdio") -> None:
    """Run the CutGraph MCP server."""
    create_server().run(transport=transport)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
