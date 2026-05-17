from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from .schema import CutGraphProject, Node
from .security import PathPolicyError, ProjectPaths


class RenderPlanError(ValueError):
    """Raised when project state cannot be compiled into a safe render plan."""


class RenderPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timeline_id: str
    preset: str
    output_path: str
    inputs: list[str]
    filtergraph: str
    argv: list[str]
    explanations: list[str]


SUPPORTED_TRANSITIONS = frozenset(
    {
        "fade",
        "wipeleft",
        "wiperight",
        "wipeup",
        "wipedown",
        "slideleft",
        "slideright",
        "slideup",
        "slidedown",
        "circlecrop",
        "rectcrop",
        "distance",
        "fadeblack",
        "fadewhite",
        "radial",
        "smoothleft",
        "smoothright",
        "smoothup",
        "smoothdown",
        "circleopen",
        "circleclose",
        "vertopen",
        "vertclose",
        "horzopen",
        "horzclose",
        "dissolve",
        "pixelize",
        "diagtl",
        "diagtr",
        "diagbl",
        "diagbr",
        "hlslice",
        "hrslice",
        "vuslice",
        "vdslice",
        "hblur",
        "fadegrays",
        "wipetl",
        "wipetr",
        "wipebl",
        "wipebr",
        "squeezeh",
        "squeezev",
        "zoomin",
        "fadefast",
        "fadeslow",
        "hlwind",
        "hrwind",
        "vuwind",
        "vdwind",
        "coverleft",
        "coverright",
        "coverup",
        "coverdown",
        "revealleft",
        "revealright",
        "revealup",
        "revealdown",
    }
)


def plan_render(
    project: CutGraphProject,
    project_root: Path | str,
    timeline_id: str,
    output_path: Path | str,
    *,
    preset: str = "final",
    ffmpeg: str = "ffmpeg",
) -> RenderPlan:
    if preset not in {"final", "preview"}:
        raise RenderPlanError("Render preset must be 'final' or 'preview'")
    try:
        timeline = project.timelines[timeline_id]
    except KeyError as exc:
        raise RenderPlanError(f"Unknown timeline {timeline_id!r}") from exc

    paths = ProjectPaths(
        project_root,
        render_dir=project.settings.render_dir,
        cache_dir=project.settings.cache_dir,
    )
    try:
        resolved_output = paths.resolve_render_output(output_path)
    except PathPolicyError as exc:
        raise RenderPlanError(str(exc)) from exc

    nodes = [_node(project, node_id) for node_id in timeline.node_ids]
    clip_nodes = [node for node in nodes if node.type == "clip"]
    if not clip_nodes:
        raise RenderPlanError(f"Timeline {timeline_id!r} has no clip nodes")

    asset_ids = _asset_ids_for_nodes(nodes)
    asset_indexes = {asset_id: index for index, asset_id in enumerate(asset_ids)}
    inputs = [_asset_path(project, paths, asset_id) for asset_id in asset_ids]

    filters: list[str] = []
    explanations = [
        "Generated an FFmpeg argv array; no shell command string is used.",
        "Source media paths are read-only inputs and project data remains the edit source of truth.",
    ]

    for index, clip in enumerate(clip_nodes):
        if clip.asset_id is None:
            raise RenderPlanError(f"Clip {clip.id!r} has no asset")
        if clip.duration is None:
            raise RenderPlanError(f"Clip {clip.id!r} needs a duration")
        input_index = asset_indexes[clip.asset_id]
        start = _fmt(clip.source_start)
        duration = _fmt(clip.duration)
        filters.append(
            f"[{input_index}:v]trim=start={start}:duration={duration},"
            f"setpts=PTS-STARTPTS[v{index}]"
        )
        filters.append(
            f"[{input_index}:a]atrim=start={start}:duration={duration},"
            f"asetpts=PTS-STARTPTS[a{index}]"
        )

    base_v, base_a = _compose_clip_sequence(filters, clip_nodes, nodes)
    current_v = base_v
    overlay_count = 0

    for node in nodes:
        if node.type == "text_overlay":
            props = node.properties
            start, end = _timing_window(props)
            enable = _enable_expression(start, end)
            label = f"vtext{overlay_count}"
            filters.append(
                f"[{current_v}]drawtext=text='{_escape_filter_quoted(str(props.get('text', '')))}':"
                f"x={_fmt_filter_number(_number_prop(props, 'x', 0))}:"
                f"y={_fmt_filter_number(_number_prop(props, 'y', 0))}:"
                f"enable='{enable}'[{label}]"
            )
            current_v = label
            overlay_count += 1
        elif node.type in {"image_overlay", "pip"}:
            if node.asset_id is None:
                raise RenderPlanError(f"Overlay {node.id!r} has no asset")
            props = node.properties
            start, end = _timing_window(props)
            enable = _enable_expression(start, end)
            scaled = f"ov{overlay_count}"
            label = f"vov{overlay_count}"
            width = _positive_int_prop(props, "width", 320)
            filters.append(f"[{asset_indexes[node.asset_id]}:v]scale={width}:-1[{scaled}]")
            filters.append(
                f"[{current_v}][{scaled}]overlay=x={_fmt_filter_number(_number_prop(props, 'x', 0))}:"
                f"y={_fmt_filter_number(_number_prop(props, 'y', 0))}:enable='{enable}'[{label}]"
            )
            current_v = label
            overlay_count += 1
        elif node.type == "subtitles":
            if node.asset_id is None:
                raise RenderPlanError(f"Subtitle node {node.id!r} has no asset")
            label = f"vsub{overlay_count}"
            subtitle_path = _escape_filter_quoted(inputs[asset_indexes[node.asset_id]])
            filters.append(f"[{current_v}]subtitles=filename='{subtitle_path}'[{label}]")
            current_v = label
            overlay_count += 1

    if preset == "preview":
        filters.append(f"[{current_v}]scale=640:-2[vout]")
        explanations.append("Preview preset adds a 640px-wide scale filter and ultrafast encoding.")
    else:
        filters.append(f"[{current_v}]null[vout]")

    filters.append(f"[{base_a}]anull[aout]")
    filtergraph = ";".join(filters)
    argv = [ffmpeg, "-nostdin", "-y"]
    for input_path in inputs:
        argv.extend(["-i", input_path])
    argv.extend(["-filter_complex", filtergraph, "-map", "[vout]", "-map", "[aout]"])
    argv.extend(["-c:v", "libx264"])
    if preset == "preview":
        argv.extend(["-preset", "ultrafast"])
    argv.extend(["-c:a", "aac", str(resolved_output)])

    return RenderPlan(
        timeline_id=timeline_id,
        preset=preset,
        output_path=str(resolved_output),
        inputs=inputs,
        filtergraph=filtergraph,
        argv=argv,
        explanations=explanations,
    )


def _compose_clip_sequence(
    filters: list[str],
    clip_nodes: list[Node],
    timeline_nodes: list[Node],
) -> tuple[str, str]:
    if len(clip_nodes) == 1:
        return "v0", "a0"

    transitions = [node for node in timeline_nodes if node.type == "transition"]
    if transitions:
        if len(transitions) > 1:
            raise RenderPlanError("Only one transition node is supported per timeline")
        if len(clip_nodes) != 2:
            raise RenderPlanError("Transition nodes currently require exactly two clips")
        transition = transitions[0]
        duration = _number_prop(transition.properties, "duration", 1.0, positive=True)
        kind = _transition_kind(transition.properties)
        first_duration = float(clip_nodes[0].duration or 0)
        offset = max(0.0, first_duration - duration)
        filters.append(
            f"[v0][v1]xfade=transition={kind}:duration={_fmt(duration)}:"
            f"offset={_fmt(offset)}[vbase]"
        )
        filters.append(f"[a0][a1]acrossfade=d={_fmt(duration)}[abase]")
        return "vbase", "abase"

    concat_inputs = "".join(f"[v{index}][a{index}]" for index in range(len(clip_nodes)))
    filters.append(f"{concat_inputs}concat=n={len(clip_nodes)}:v=1:a=1[vbase][abase]")
    return "vbase", "abase"


def _asset_ids_for_nodes(nodes: list[Node]) -> list[str]:
    asset_ids: list[str] = []
    for node in nodes:
        if node.asset_id and node.asset_id not in asset_ids:
            asset_ids.append(node.asset_id)
    return asset_ids


def _asset_path(project: CutGraphProject, paths: ProjectPaths, asset_id: str) -> str:
    try:
        asset = project.assets[asset_id]
    except KeyError as exc:
        raise RenderPlanError(f"Unknown asset {asset_id!r}") from exc
    try:
        return str(paths.resolve_project_path(asset.path))
    except PathPolicyError as exc:
        raise RenderPlanError(str(exc)) from exc


def _node(project: CutGraphProject, node_id: str) -> Node:
    try:
        return project.nodes[node_id]
    except KeyError as exc:
        raise RenderPlanError(f"Timeline references unknown node {node_id!r}") from exc


def _timing_window(props: dict[str, Any]) -> tuple[str, str]:
    start = _number_prop(props, "start", 0.0, minimum=0.0)
    if props.get("duration") is None:
        return _fmt(start), ""
    duration = _number_prop(props, "duration", 0.0, positive=True)
    return _fmt(start), _fmt(start + duration)


def _enable_expression(start: str, end: str) -> str:
    if not end:
        return f"gte(t,{start})"
    return f"between(t,{start},{end})"


def _number_prop(
    props: dict[str, Any],
    key: str,
    default: float,
    *,
    minimum: float | None = None,
    positive: bool = False,
) -> float:
    raw = props.get(key, default)
    if isinstance(raw, bool):
        raise RenderPlanError(f"{key} must be numeric")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise RenderPlanError(f"{key} must be numeric") from exc
    if not math.isfinite(value):
        raise RenderPlanError(f"{key} must be finite")
    if positive and value <= 0:
        raise RenderPlanError(f"{key} must be positive")
    if minimum is not None and value < minimum:
        raise RenderPlanError(f"{key} must be at least {_fmt_filter_number(minimum)}")
    return value


def _positive_int_prop(props: dict[str, Any], key: str, default: int) -> int:
    value = _number_prop(props, key, default, positive=True)
    if not value.is_integer():
        raise RenderPlanError(f"{key} must be an integer")
    return int(value)


def _transition_kind(props: dict[str, Any]) -> str:
    kind = props.get("kind", "fade")
    if not isinstance(kind, str) or kind not in SUPPORTED_TRANSITIONS:
        raise RenderPlanError(f"Unsupported transition {kind!r}")
    return kind


def _fmt(value: float) -> str:
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    if "." not in text:
        text += ".0"
    return text


def _fmt_filter_number(value: float) -> str:
    return f"{float(value):.6f}".rstrip("0").rstrip(".")


def _escape_filter_quoted(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "\\'")
