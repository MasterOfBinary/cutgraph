from __future__ import annotations

from .schema import CutGraphProject, Node, Timeline


def create_timeline(project: CutGraphProject, timeline_id: str, name: str) -> Timeline:
    if timeline_id in project.timelines:
        raise ValueError(f"Timeline {timeline_id!r} already exists")
    timeline = Timeline(id=timeline_id, name=name)
    project.timelines[timeline_id] = timeline
    return timeline


def add_clip(
    project: CutGraphProject,
    timeline_id: str,
    asset_id: str,
    *,
    node_id: str | None = None,
    source_start: float = 0.0,
    duration: float,
) -> Node:
    timeline = _timeline(project, timeline_id)
    if asset_id not in project.assets:
        raise ValueError(f"Unknown asset {asset_id!r}")
    node_id = node_id or _unique_id(project, f"{asset_id}_clip")
    if node_id in project.nodes:
        raise ValueError(f"Node {node_id!r} already exists")
    node = Node(
        id=node_id,
        type="clip",
        asset_id=asset_id,
        source_start=_non_negative(source_start, "source_start"),
        duration=_positive(duration, "duration"),
    )
    project.nodes[node.id] = node
    timeline.node_ids.append(node.id)
    return node


def trim_clip(
    project: CutGraphProject,
    node_id: str,
    *,
    source_start: float | None = None,
    duration: float | None = None,
) -> Node:
    node = _node(project, node_id)
    if source_start is not None:
        node.source_start = _non_negative(source_start, "source_start")
    if duration is not None:
        node.duration = _positive(duration, "duration")
    return node


def split_clip(
    project: CutGraphProject,
    timeline_id: str,
    node_id: str,
    *,
    at: float,
) -> tuple[Node, Node]:
    timeline = _timeline(project, timeline_id)
    node = _node(project, node_id)
    if node.duration is None or at <= 0 or at >= node.duration:
        raise ValueError("Split point must be inside clip duration")
    if node_id not in timeline.node_ids:
        raise ValueError(f"Node {node_id!r} is not in timeline {timeline_id!r}")

    left = node.model_copy(
        update={
            "id": _unique_id(project, f"{node_id}_a"),
            "duration": at,
        }
    )
    right = node.model_copy(
        update={
            "id": _unique_id(project, f"{node_id}_b"),
            "source_start": node.source_start + at,
            "duration": node.duration - at,
        }
    )

    index = timeline.node_ids.index(node_id)
    timeline.node_ids[index : index + 1] = [left.id, right.id]
    project.nodes.pop(node_id)
    project.nodes[left.id] = left
    project.nodes[right.id] = right
    return left, right


def move_clip(
    project: CutGraphProject,
    timeline_id: str,
    node_id: str,
    *,
    index: int,
) -> None:
    timeline = _timeline(project, timeline_id)
    if node_id not in timeline.node_ids:
        raise ValueError(f"Node {node_id!r} is not in timeline {timeline_id!r}")
    timeline.node_ids.remove(node_id)
    if index < 0 or index > len(timeline.node_ids):
        raise ValueError("Move index is outside timeline bounds")
    timeline.node_ids.insert(index, node_id)


def delete_clip(project: CutGraphProject, timeline_id: str, node_id: str) -> None:
    timeline = _timeline(project, timeline_id)
    if node_id not in timeline.node_ids:
        raise ValueError(f"Node {node_id!r} is not in timeline {timeline_id!r}")
    timeline.node_ids.remove(node_id)
    project.nodes.pop(node_id, None)


def _timeline(project: CutGraphProject, timeline_id: str) -> Timeline:
    try:
        return project.timelines[timeline_id]
    except KeyError as exc:
        raise ValueError(f"Unknown timeline {timeline_id!r}") from exc


def _node(project: CutGraphProject, node_id: str) -> Node:
    try:
        return project.nodes[node_id]
    except KeyError as exc:
        raise ValueError(f"Unknown node {node_id!r}") from exc


def _positive(value: float, name: str) -> float:
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return float(value)


def _non_negative(value: float, name: str) -> float:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return float(value)


def _unique_id(project: CutGraphProject, prefix: str) -> str:
    candidate = prefix
    suffix = 2
    while candidate in project.nodes:
        candidate = f"{prefix}_{suffix}"
        suffix += 1
    return candidate
