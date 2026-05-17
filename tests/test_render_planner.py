from pathlib import Path

import pytest

from cutgraph.render import RenderPlanError, plan_render
from cutgraph.schema import Asset, CutGraphProject, Node, ProjectSettings, Timeline


def test_planner_builds_argv_filtergraph_for_trimmed_concat(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)

    plan = plan_render(project, project_root, "main", "renders/out.mp4")

    assert isinstance(plan.argv, list)
    assert plan.argv[0] == "ffmpeg"
    assert "-filter_complex" in plan.argv
    assert "trim=start=1.5:duration=3.0" in plan.filtergraph
    assert "atrim=start=1.5:duration=3.0" in plan.filtergraph
    assert "trim=start=0.0:duration=4.0" in plan.filtergraph
    assert "concat=n=2:v=1:a=1" in plan.filtergraph
    assert plan.argv[-1].endswith("renders/out.mp4")
    assert any("argv" in item.lower() for item in plan.explanations)


def test_planner_adds_text_image_pip_and_subtitle_filters(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)
    project.nodes["title"] = Node(
        id="title",
        type="text_overlay",
        properties={"text": "Hello CutGraph", "x": 24, "y": 32, "start": 1, "duration": 3},
    )
    project.nodes["logo"] = Node(
        id="logo",
        type="image_overlay",
        asset_id="logo",
        properties={"x": 10, "y": 20, "width": 200, "start": 0, "duration": 2},
    )
    project.nodes["pip"] = Node(
        id="pip",
        type="pip",
        asset_id="clip_b",
        properties={"x": 960, "y": 540, "width": 320, "start": 2, "duration": 4},
    )
    project.nodes["subs"] = Node(id="subs", type="subtitles", asset_id="subs")
    project.timelines["main"].node_ids.extend(["title", "logo", "pip", "subs"])

    plan = plan_render(project, project_root, "main", "renders/out.mp4")

    assert "drawtext" in plan.filtergraph
    assert "Hello CutGraph" in plan.filtergraph
    assert "overlay=x=10:y=20" in plan.filtergraph
    assert "overlay=x=960:y=540" in plan.filtergraph
    assert "scale=200:-1" in plan.filtergraph
    assert "scale=320:-1" in plan.filtergraph
    assert "subtitles=" in plan.filtergraph


@pytest.mark.parametrize(
    ("node_type", "properties"),
    [
        ("image_overlay", {"x": "0,drawbox=c=red", "y": 20, "width": 200}),
        ("pip", {"x": 10, "y": "20;movie=/etc/passwd", "width": 200}),
        ("image_overlay", {"x": 10, "y": 20, "width": "200,drawbox=c=red"}),
    ],
)
def test_planner_rejects_filtergraph_injection_in_numeric_overlay_props(
    tmp_path: Path,
    node_type: str,
    properties: dict[str, object],
) -> None:
    project_root, project = make_project(tmp_path)
    project.nodes["overlay"] = Node(
        id="overlay",
        type=node_type,
        asset_id="logo",
        properties=properties,
    )
    project.timelines["main"].node_ids.append("overlay")

    with pytest.raises(RenderPlanError, match="must be"):
        plan_render(project, project_root, "main", "renders/out.mp4")


def test_planner_rejects_filtergraph_injection_in_transition_kind(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)
    project.nodes["bad_transition"] = Node(
        id="bad_transition",
        type="transition",
        properties={"kind": "fade,drawbox=c=red", "duration": 1.0},
    )
    project.timelines["main"].node_ids = ["clip1", "bad_transition", "clip2"]

    with pytest.raises(RenderPlanError, match="Unsupported transition"):
        plan_render(project, project_root, "main", "renders/out.mp4")


def test_planner_quotes_and_escapes_subtitle_filter_paths(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)
    subtitle_path = project_root / "media" / "caption,semi;[0]'s.srt"
    subtitle_path.write_bytes(b"placeholder")
    project.assets["subs"].path = "media/caption,semi;[0]'s.srt"
    project.nodes["subs"] = Node(id="subs", type="subtitles", asset_id="subs")
    project.timelines["main"].node_ids.append("subs")

    plan = plan_render(project, project_root, "main", "renders/out.mp4")

    assert "subtitles=filename='" in plan.filtergraph
    assert "\\'s.srt'" in plan.filtergraph


def test_planner_uses_xfade_for_transition_nodes(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)
    project.nodes["fade"] = Node(
        id="fade",
        type="transition",
        properties={"kind": "fade", "duration": 1.0},
    )
    project.timelines["main"].node_ids = ["clip1", "fade", "clip2"]

    plan = plan_render(project, project_root, "main", "renders/out.mp4")

    assert "xfade=transition=fade:duration=1.0" in plan.filtergraph
    assert "acrossfade=d=1.0" in plan.filtergraph


def test_planner_rejects_transitions_it_cannot_apply(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)
    project.nodes["clip3"] = Node(
        id="clip3",
        type="clip",
        asset_id="clip_a",
        source_start=0.0,
        duration=2.0,
    )
    project.nodes["fade"] = Node(
        id="fade",
        type="transition",
        properties={"kind": "fade", "duration": 1.0},
    )
    project.timelines["main"].node_ids = ["clip1", "fade", "clip2", "clip3"]

    with pytest.raises(RenderPlanError, match="exactly two clips"):
        plan_render(project, project_root, "main", "renders/out.mp4")


def test_preview_plan_adds_preview_scale(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)

    plan = plan_render(project, project_root, "main", "renders/preview.mp4", preset="preview")

    assert "scale=640:-2" in plan.filtergraph
    assert "ultrafast" in plan.argv


def test_planner_rejects_outputs_outside_renders(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)

    with pytest.raises(RenderPlanError, match="renders"):
        plan_render(project, project_root, "main", "out.mp4")


def test_planner_rejects_empty_timeline(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)
    project.timelines["empty"] = Timeline(id="empty", name="Empty")

    with pytest.raises(RenderPlanError, match="no clip nodes"):
        plan_render(project, project_root, "empty", "renders/out.mp4")


def test_planner_rejects_clip_without_duration(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)
    project.nodes["clip1"].duration = None

    with pytest.raises(RenderPlanError, match="needs a duration"):
        plan_render(project, project_root, "main", "renders/out.mp4")


def make_project(tmp_path: Path) -> tuple[Path, CutGraphProject]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    for relative in ["media/a.mp4", "media/b.mp4", "media/logo.png", "captions.srt"]:
        path = project_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"placeholder")

    project = CutGraphProject(
        settings=ProjectSettings(),
        assets={
            "clip_a": Asset(id="clip_a", path="media/a.mp4", media_type="video"),
            "clip_b": Asset(id="clip_b", path="media/b.mp4", media_type="video"),
            "logo": Asset(id="logo", path="media/logo.png", media_type="image"),
            "subs": Asset(id="subs", path="captions.srt", media_type="subtitle"),
        },
        nodes={
            "clip1": Node(
                id="clip1",
                type="clip",
                asset_id="clip_a",
                source_start=1.5,
                duration=3.0,
            ),
            "clip2": Node(
                id="clip2",
                type="clip",
                asset_id="clip_b",
                source_start=0.0,
                duration=4.0,
            ),
        },
        timelines={
            "main": Timeline(id="main", name="Main", node_ids=["clip1", "clip2"]),
        },
    )
    return project_root, project
