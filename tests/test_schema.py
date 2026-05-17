import pytest
from pydantic import ValidationError

from cutgraph.schema import CutGraphProject, Node, ProjectSettings, RenderRecord, Timeline


def test_minimal_project_defaults_to_v01_schema() -> None:
    project = CutGraphProject(settings=ProjectSettings())

    assert project.version == "0.1"
    assert project.settings.render_dir == "renders"
    assert project.settings.cache_dir == ".cutgraph/cache"
    assert project.assets == {}
    assert project.timelines == {}
    assert project.nodes == {}
    assert project.renders == {}


def test_timeline_rejects_unknown_node_references() -> None:
    with pytest.raises(ValidationError, match="unknown node"):
        CutGraphProject(
            settings=ProjectSettings(),
            timelines={
                "main": Timeline(id="main", name="Main", node_ids=["missing"]),
            },
        )


def test_node_rejects_unknown_asset_reference() -> None:
    with pytest.raises(ValidationError, match="unknown asset"):
        CutGraphProject(
            settings=ProjectSettings(),
            nodes={
                "clip1": Node(
                    id="clip1",
                    type="clip",
                    asset_id="missing",
                    duration=3.0,
                )
            },
        )


def test_render_rejects_unknown_timeline_reference() -> None:
    with pytest.raises(ValidationError, match="unknown timeline"):
        CutGraphProject(
            settings=ProjectSettings(),
            renders={
                "r1": RenderRecord(
                    id="r1",
                    timeline_id="missing",
                    output_path="renders/out.mp4",
                )
            },
        )
