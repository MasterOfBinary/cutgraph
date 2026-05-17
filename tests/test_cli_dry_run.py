import json
from pathlib import Path

from typer.testing import CliRunner

from cutgraph.cli import app
from cutgraph.schema import Asset, CutGraphProject, Node, ProjectSettings, Timeline
from cutgraph.store import save_project


runner = CliRunner()


def test_dry_run_cli_preserves_ffmpeg_filter_labels(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    (project_root / "media").mkdir(parents=True)
    project_root.joinpath("media/a.mp4").write_bytes(b"a")
    project_root.joinpath("media/b.mp4").write_bytes(b"b")
    project = CutGraphProject(
        settings=ProjectSettings(),
        assets={
            "a": Asset(id="a", path="media/a.mp4", media_type="video"),
            "b": Asset(id="b", path="media/b.mp4", media_type="video"),
        },
        nodes={
            "clip_a": Node(id="clip_a", type="clip", asset_id="a", duration=1),
            "clip_b": Node(id="clip_b", type="clip", asset_id="b", duration=1),
        },
        timelines={
            "main": Timeline(id="main", name="Main", node_ids=["clip_a", "clip_b"])
        },
    )
    save_project(project_root, project)

    result = runner.invoke(app, ["dry-run", str(project_root), "main", "renders/out.mp4"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "[vbase]" in payload["filtergraph"]
    assert "[abase]" in payload["filtergraph"]
    assert "[vout]" in payload["argv"]
    assert "[aout]" in payload["argv"]
