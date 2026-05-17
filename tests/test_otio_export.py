import json
from pathlib import Path

import pytest

from cutgraph.otio_export import export_otio
from cutgraph.schema import Asset, CutGraphProject, Node, ProjectSettings, Timeline
from cutgraph.security import PathPolicyError


def test_export_otio_writes_timeline_json_without_optional_dependency(tmp_path: Path) -> None:
    project = CutGraphProject(
        settings=ProjectSettings(),
        assets={"clip_a": Asset(id="clip_a", path="media/a.mp4", media_type="video")},
        nodes={
            "clip1": Node(
                id="clip1",
                type="clip",
                asset_id="clip_a",
                source_start=2.0,
                duration=5.0,
            )
        },
        timelines={"main": Timeline(id="main", name="Main", node_ids=["clip1"])},
    )
    output = tmp_path / "main.otio"

    payload = export_otio(project, "main", output)
    loaded = json.loads(output.read_text(encoding="utf-8"))

    assert json.loads(payload) == loaded
    assert loaded["OTIO_SCHEMA"] == "Timeline.1"
    assert loaded["name"] == "Main"
    clip = loaded["tracks"]["children"][0]["children"][0]
    assert clip["name"] == "clip1"
    assert clip["media_reference"]["target_url"] == "media/a.mp4"
    assert clip["source_range"]["start_time"]["value"] == 2.0
    assert clip["source_range"]["duration"]["value"] == 5.0


def test_export_otio_rejects_output_outside_project_when_root_is_provided(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    project = make_project()

    with pytest.raises(PathPolicyError, match="outside project root"):
        export_otio(project, "main", "../escape.otio", project_root=project_root)


def make_project() -> CutGraphProject:
    return CutGraphProject(
        settings=ProjectSettings(),
        assets={"clip_a": Asset(id="clip_a", path="media/a.mp4", media_type="video")},
        nodes={
            "clip1": Node(
                id="clip1",
                type="clip",
                asset_id="clip_a",
                source_start=2.0,
                duration=5.0,
            )
        },
        timelines={"main": Timeline(id="main", name="Main", node_ids=["clip1"])},
    )
