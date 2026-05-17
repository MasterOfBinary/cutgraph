from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import CutGraphProject, Node
from .security import ProjectPaths


def export_otio(
    project: CutGraphProject,
    timeline_id: str,
    output_path: Path | str | None = None,
    *,
    project_root: Path | str | None = None,
) -> str:
    payload = json.dumps(build_otio_dict(project, timeline_id), indent=2) + "\n"
    if output_path is not None:
        if project_root is None:
            path = Path(output_path)
        else:
            path = ProjectPaths(project_root).resolve_project_path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    return payload


def build_otio_dict(project: CutGraphProject, timeline_id: str) -> dict[str, Any]:
    try:
        timeline = project.timelines[timeline_id]
    except KeyError as exc:
        raise ValueError(f"Unknown timeline {timeline_id!r}") from exc

    clips = [
        _clip_to_otio(project, project.nodes[node_id])
        for node_id in timeline.node_ids
        if project.nodes[node_id].type == "clip"
    ]
    return {
        "OTIO_SCHEMA": "Timeline.1",
        "name": timeline.name,
        "tracks": {
            "OTIO_SCHEMA": "Stack.1",
            "children": [
                {
                    "OTIO_SCHEMA": "Track.1",
                    "name": "Video",
                    "kind": "Video",
                    "children": clips,
                }
            ],
        },
        "metadata": {"cutgraph_version": project.version},
    }


def _clip_to_otio(project: CutGraphProject, node: Node) -> dict[str, Any]:
    if node.asset_id is None:
        raise ValueError(f"Clip {node.id!r} has no asset")
    asset = project.assets[node.asset_id]
    rate = project.settings.frame_rate
    return {
        "OTIO_SCHEMA": "Clip.2",
        "name": node.id,
        "media_reference": {
            "OTIO_SCHEMA": "ExternalReference.1",
            "target_url": asset.path,
            "available_range": None,
            "metadata": {"cutgraph_asset_id": asset.id},
        },
        "source_range": {
            "OTIO_SCHEMA": "TimeRange.1",
            "start_time": {
                "OTIO_SCHEMA": "RationalTime.1",
                "value": node.source_start,
                "rate": rate,
            },
            "duration": {
                "OTIO_SCHEMA": "RationalTime.1",
                "value": node.duration or 0,
                "rate": rate,
            },
        },
        "metadata": {"cutgraph_node_id": node.id},
    }
