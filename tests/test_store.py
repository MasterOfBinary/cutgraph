from pathlib import Path

import pytest

from cutgraph.schema import CutGraphProject, ProjectSettings
from cutgraph.store import create_project, load_project, save_project


def test_create_project_writes_cutgraph_json(tmp_path: Path) -> None:
    project_root = tmp_path / "movie"

    project = create_project(project_root)

    assert project_root.joinpath(".cutgraph.json").is_file()
    assert project.version == "0.1"
    assert load_project(project_root).version == "0.1"


def test_save_project_round_trips_typed_project(tmp_path: Path) -> None:
    project_root = tmp_path / "movie"
    project_root.mkdir()
    project = CutGraphProject(settings=ProjectSettings(width=1280, height=720))

    save_project(project_root, project)

    loaded = load_project(project_root)
    assert loaded.settings.width == 1280
    assert loaded.settings.height == 720


def test_load_project_reports_invalid_json(tmp_path: Path) -> None:
    project_root = tmp_path / "movie"
    project_root.mkdir()
    project_root.joinpath(".cutgraph.json").write_text("{nope", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_project(project_root)
