from pathlib import Path

from typer.testing import CliRunner

from cutgraph.cli import app
from cutgraph.store import create_project


runner = CliRunner()


def test_validate_cli_accepts_valid_project(tmp_path: Path) -> None:
    project_root = tmp_path / "movie"
    create_project(project_root)

    result = runner.invoke(app, ["validate", str(project_root)])

    assert result.exit_code == 0
    assert "valid" in result.output.lower()


def test_validate_cli_rejects_invalid_project(tmp_path: Path) -> None:
    project_root = tmp_path / "movie"
    project_root.mkdir()
    project_root.joinpath(".cutgraph.json").write_text("{nope", encoding="utf-8")

    result = runner.invoke(app, ["validate", str(project_root)])

    assert result.exit_code == 1
    assert "invalid" in result.output.lower()
