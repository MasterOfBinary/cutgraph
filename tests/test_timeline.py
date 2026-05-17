from pathlib import Path

import pytest

from cutgraph.schema import Asset, CutGraphProject, ProjectSettings
from cutgraph.timeline import (
    add_clip,
    create_timeline,
    delete_clip,
    move_clip,
    split_clip,
    trim_clip,
)


def test_clip_operations_mutate_project_data_not_source_media(tmp_path: Path) -> None:
    media = tmp_path / "source.mp4"
    media.write_bytes(b"original")
    project = CutGraphProject(
        settings=ProjectSettings(),
        assets={"a1": Asset(id="a1", path="source.mp4")},
    )
    create_timeline(project, "main", "Main")

    clip = add_clip(project, "main", "a1", node_id="clip1", duration=10.0)
    trim_clip(project, "clip1", source_start=2.0, duration=6.0)
    left, right = split_clip(project, "main", "clip1", at=3.0)

    assert clip.asset_id == "a1"
    assert project.timelines["main"].node_ids == [left.id, right.id]
    assert project.nodes[left.id].source_start == 2.0
    assert project.nodes[left.id].duration == 3.0
    assert project.nodes[right.id].source_start == 5.0
    assert project.nodes[right.id].duration == 3.0
    assert media.read_bytes() == b"original"


def test_move_and_delete_clip_preserve_assets() -> None:
    project = CutGraphProject(
        settings=ProjectSettings(),
        assets={"a1": Asset(id="a1", path="source.mp4")},
    )
    create_timeline(project, "main", "Main")
    add_clip(project, "main", "a1", node_id="first", duration=1)
    add_clip(project, "main", "a1", node_id="second", duration=1)

    move_clip(project, "main", "second", index=0)
    delete_clip(project, "main", "first")

    assert project.timelines["main"].node_ids == ["second"]
    assert "first" not in project.nodes
    assert "a1" in project.assets


def test_split_rejects_points_outside_clip_duration() -> None:
    project = CutGraphProject(
        settings=ProjectSettings(),
        assets={"a1": Asset(id="a1", path="source.mp4")},
    )
    create_timeline(project, "main", "Main")
    add_clip(project, "main", "a1", node_id="clip1", duration=5)

    with pytest.raises(ValueError, match="inside clip duration"):
        split_clip(project, "main", "clip1", at=5)


def test_move_clip_rejects_out_of_bounds_index() -> None:
    project = CutGraphProject(
        settings=ProjectSettings(),
        assets={"a1": Asset(id="a1", path="source.mp4")},
    )
    create_timeline(project, "main", "Main")
    add_clip(project, "main", "a1", node_id="clip1", duration=5)

    with pytest.raises(ValueError, match="outside timeline bounds"):
        move_clip(project, "main", "clip1", index=2)
