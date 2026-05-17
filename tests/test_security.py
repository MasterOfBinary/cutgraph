from pathlib import Path

import pytest

from cutgraph.security import PathPolicyError, ProjectPaths


def test_resolve_media_path_allows_files_inside_project(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    media = project_root / "media" / "clip.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"not real video")

    paths = ProjectPaths(project_root)

    assert paths.resolve_project_path("media/clip.mp4") == media.resolve()


def test_resolve_media_path_rejects_escape_from_project_root(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    paths = ProjectPaths(project_root)

    with pytest.raises(PathPolicyError, match="outside project root"):
        paths.resolve_project_path("../escape.mp4")


def test_resolve_render_output_requires_renders_directory(tmp_path: Path) -> None:
    paths = ProjectPaths(tmp_path / "project")

    assert paths.resolve_render_output("renders/out.mp4").parent.name == "renders"

    with pytest.raises(PathPolicyError, match="renders"):
        paths.resolve_render_output("out.mp4")


def test_resolve_project_path_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    project_root = tmp_path / "project"
    project_root.mkdir()
    project_root.joinpath("linked").symlink_to(outside)

    paths = ProjectPaths(project_root)

    with pytest.raises(PathPolicyError, match="outside project root"):
        paths.resolve_project_path("linked/file.mp4")
