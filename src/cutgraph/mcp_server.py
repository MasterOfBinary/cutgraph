from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .media import probe_asset as probe_project_asset
from .otio_export import export_otio as export_project_otio
from .render import plan_render as plan_project_render
from .render import SUPPORTED_TRANSITIONS
from .render_jobs import (
    cancel_render as cancel_project_render,
    render_status as get_project_render_status,
    start_render as start_project_render,
)
from .schema import Node
from .store import create_project as create_project_store
from .store import load_project, save_project
from .timeline import (
    add_clip as add_project_clip,
    create_timeline as create_project_timeline,
    delete_clip as delete_project_clip,
    move_clip as move_project_clip,
    split_clip as split_project_clip,
    trim_clip as trim_project_clip,
)


REQUIRED_TOOL_NAMES = [
    "create_project",
    "validate_project",
    "project_info",
    "probe_asset",
    "create_timeline",
    "add_clip",
    "trim_clip",
    "split_clip",
    "move_clip",
    "delete_clip",
    "add_text_overlay",
    "add_overlay",
    "add_pip",
    "add_subtitles",
    "add_transition",
    "plan_render",
    "start_render",
    "render_status",
    "cancel_render",
    "export_otio",
]


def create_server() -> FastMCP:
    server = FastMCP("CutGraph")

    @server.tool(name="create_project")
    def create_project(project_root: str) -> dict[str, Any]:
        project = create_project_store(Path(project_root))
        return {"project_root": project_root, "project": project.model_dump(mode="json")}

    @server.tool(name="validate_project")
    def validate_project(project_root: str) -> dict[str, Any]:
        project = load_project(project_root)
        return {"valid": True, "version": project.version}

    @server.tool(name="project_info")
    def project_info(project_root: str) -> dict[str, Any]:
        project = load_project(project_root)
        return {
            "version": project.version,
            "asset_count": len(project.assets),
            "timeline_count": len(project.timelines),
            "render_count": len(project.renders),
        }

    @server.tool(name="probe_asset")
    def probe_asset(project_root: str, media_path: str, asset_id: str | None = None) -> dict[str, Any]:
        project = load_project(project_root)
        asset = probe_project_asset(project, project_root, media_path, asset_id=asset_id)
        save_project(project_root, project)
        return asset.model_dump(mode="json")

    @server.tool(name="create_timeline")
    def create_timeline(project_root: str, timeline_id: str, name: str) -> dict[str, Any]:
        project = load_project(project_root)
        timeline = create_project_timeline(project, timeline_id, name)
        save_project(project_root, project)
        return timeline.model_dump(mode="json")

    @server.tool(name="add_clip")
    def add_clip(
        project_root: str,
        timeline_id: str,
        asset_id: str,
        duration: float,
        node_id: str | None = None,
        source_start: float = 0.0,
    ) -> dict[str, Any]:
        project = load_project(project_root)
        node = add_project_clip(
            project,
            timeline_id,
            asset_id,
            node_id=node_id,
            source_start=source_start,
            duration=duration,
        )
        save_project(project_root, project)
        return node.model_dump(mode="json")

    @server.tool(name="trim_clip")
    def trim_clip(
        project_root: str,
        node_id: str,
        source_start: float | None = None,
        duration: float | None = None,
    ) -> dict[str, Any]:
        project = load_project(project_root)
        node = trim_project_clip(
            project,
            node_id,
            source_start=source_start,
            duration=duration,
        )
        save_project(project_root, project)
        return node.model_dump(mode="json")

    @server.tool(name="split_clip")
    def split_clip(project_root: str, timeline_id: str, node_id: str, at: float) -> dict[str, Any]:
        project = load_project(project_root)
        left, right = split_project_clip(project, timeline_id, node_id, at=at)
        save_project(project_root, project)
        return {"left": left.model_dump(mode="json"), "right": right.model_dump(mode="json")}

    @server.tool(name="move_clip")
    def move_clip(project_root: str, timeline_id: str, node_id: str, index: int) -> dict[str, Any]:
        project = load_project(project_root)
        move_project_clip(project, timeline_id, node_id, index=index)
        save_project(project_root, project)
        return {"moved": node_id, "index": index}

    @server.tool(name="delete_clip")
    def delete_clip(project_root: str, timeline_id: str, node_id: str) -> dict[str, Any]:
        project = load_project(project_root)
        delete_project_clip(project, timeline_id, node_id)
        save_project(project_root, project)
        return {"deleted": node_id}

    @server.tool(name="add_text_overlay")
    def add_text_overlay(
        project_root: str,
        timeline_id: str,
        node_id: str,
        text: str,
        x: int = 0,
        y: int = 0,
        start: float = 0.0,
        duration: float | None = None,
    ) -> dict[str, Any]:
        return _append_node(
            project_root,
            timeline_id,
            Node(
                id=node_id,
                type="text_overlay",
                properties=_overlay_properties(
                    {"text": text, "x": x, "y": y},
                    start=start,
                    duration=duration,
                ),
            ),
        )

    @server.tool(name="add_overlay")
    def add_overlay(
        project_root: str,
        timeline_id: str,
        node_id: str,
        asset_id: str,
        x: int = 0,
        y: int = 0,
        width: int = 320,
        start: float = 0.0,
        duration: float | None = None,
    ) -> dict[str, Any]:
        return _append_node(
            project_root,
            timeline_id,
            Node(
                id=node_id,
                type="image_overlay",
                asset_id=asset_id,
                properties=_overlay_properties(
                    {"x": x, "y": y, "width": width},
                    start=start,
                    duration=duration,
                ),
            ),
        )

    @server.tool(name="add_pip")
    def add_pip(
        project_root: str,
        timeline_id: str,
        node_id: str,
        asset_id: str,
        x: int = 0,
        y: int = 0,
        width: int = 320,
        start: float = 0.0,
        duration: float | None = None,
    ) -> dict[str, Any]:
        return _append_node(
            project_root,
            timeline_id,
            Node(
                id=node_id,
                type="pip",
                asset_id=asset_id,
                properties=_overlay_properties(
                    {"x": x, "y": y, "width": width},
                    start=start,
                    duration=duration,
                ),
            ),
        )

    @server.tool(name="add_subtitles")
    def add_subtitles(project_root: str, timeline_id: str, node_id: str, asset_id: str) -> dict[str, Any]:
        return _append_node(
            project_root,
            timeline_id,
            Node(id=node_id, type="subtitles", asset_id=asset_id),
        )

    @server.tool(name="add_transition")
    def add_transition(
        project_root: str,
        timeline_id: str,
        node_id: str,
        kind: str = "fade",
        duration: float = 1.0,
        index: int | None = None,
    ) -> dict[str, Any]:
        if kind not in SUPPORTED_TRANSITIONS:
            raise ValueError(f"Unsupported transition {kind!r}")
        return _append_node(
            project_root,
            timeline_id,
            Node(id=node_id, type="transition", properties={"kind": kind, "duration": duration}),
            index=index,
        )

    @server.tool(name="plan_render")
    def plan_render(
        project_root: str,
        timeline_id: str,
        output_path: str,
        preset: str = "final",
    ) -> dict[str, Any]:
        project = load_project(project_root)
        plan = plan_project_render(project, project_root, timeline_id, output_path, preset=preset)
        return plan.model_dump(mode="json")

    @server.tool(name="start_render")
    def start_render(
        project_root: str,
        timeline_id: str,
        output_path: str,
        preset: str = "final",
    ) -> dict[str, Any]:
        project = load_project(project_root)
        record = start_project_render(project, project_root, timeline_id, output_path, preset=preset)
        save_project(project_root, project)
        return record.model_dump(mode="json")

    @server.tool(name="render_status")
    def render_status(project_root: str, render_id: str) -> dict[str, Any]:
        project = load_project(project_root)
        return get_project_render_status(project, render_id).model_dump(mode="json")

    @server.tool(name="cancel_render")
    def cancel_render(project_root: str, render_id: str) -> dict[str, Any]:
        project = load_project(project_root)
        record = cancel_project_render(project, render_id)
        save_project(project_root, project)
        return record.model_dump(mode="json")

    @server.tool(name="export_otio")
    def export_otio(project_root: str, timeline_id: str, output_path: str | None = None) -> str:
        project = load_project(project_root)
        return export_project_otio(project, timeline_id, output_path, project_root=project_root)

    return server


def _append_node(
    project_root: str,
    timeline_id: str,
    node: Node,
    *,
    index: int | None = None,
) -> dict[str, Any]:
    project = load_project(project_root)
    if node.id in project.nodes:
        raise ValueError(f"Node {node.id!r} already exists")
    if node.asset_id is not None and node.asset_id not in project.assets:
        raise ValueError(f"Unknown asset {node.asset_id!r}")
    try:
        timeline = project.timelines[timeline_id]
    except KeyError as exc:
        raise ValueError(f"Unknown timeline {timeline_id!r}") from exc
    if index is not None and (index < 0 or index > len(timeline.node_ids)):
        raise ValueError("Node index is outside timeline bounds")
    project.nodes[node.id] = node
    if index is None:
        timeline.node_ids.append(node.id)
    else:
        timeline.node_ids.insert(index, node.id)
    save_project(project_root, project)
    return node.model_dump(mode="json")


def _overlay_properties(
    values: dict[str, Any],
    *,
    start: float,
    duration: float | None,
) -> dict[str, Any]:
    if start < 0:
        raise ValueError("start must be non-negative")
    if duration is not None and duration <= 0:
        raise ValueError("duration must be positive")
    properties = {**values, "start": float(start)}
    if duration is not None:
        properties["duration"] = float(duration)
    return properties
