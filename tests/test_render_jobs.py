from pathlib import Path
from subprocess import CompletedProcess
from threading import Event

import pytest

from cutgraph.render_jobs import (
    RenderExecutionError,
    cancel_render,
    render_status,
    run_render,
    start_render,
)
from cutgraph.schema import Asset, CutGraphProject, Node, ProjectSettings, RenderRecord, Timeline


def test_run_render_executes_ffmpeg_argv_and_records_completion(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)
    calls: list[list[str]] = []

    def fake_run(argv: list[str]) -> CompletedProcess[str]:
        calls.append(argv)
        return CompletedProcess(argv, 0, stdout="", stderr="")

    record = run_render(
        project,
        project_root,
        "main",
        "renders/out.mp4",
        runner=fake_run,
    )

    assert calls == [record.plan["argv"]]
    assert record.status == "completed"
    assert record.error is None
    assert record.id in project.renders
    assert record.plan["argv"][0] == "ffmpeg"
    assert isinstance(record.plan["argv"], list)


def test_run_render_records_failed_ffmpeg_result(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)

    def failing_run(argv: list[str]) -> CompletedProcess[str]:
        return CompletedProcess(argv, 1, stdout="", stderr="encoder failed")

    with pytest.raises(RenderExecutionError, match="encoder failed"):
        run_render(project, project_root, "main", "renders/out.mp4", runner=failing_run)

    record = next(iter(project.renders.values()))
    assert record.status == "failed"
    assert "encoder failed" in (record.error or "")


def test_run_render_reports_missing_ffmpeg(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)

    def missing_ffmpeg(_argv: list[str]) -> CompletedProcess[str]:
        raise FileNotFoundError("ffmpeg")

    with pytest.raises(RenderExecutionError, match="FFmpeg"):
        run_render(project, project_root, "main", "renders/out.mp4", runner=missing_ffmpeg)

    record = next(iter(project.renders.values()))
    assert record.status == "failed"
    assert "FFmpeg" in (record.error or "")


def test_render_status_and_cancel_update_project_record(tmp_path: Path) -> None:
    _project_root, project = make_project(tmp_path)
    project.renders["r1"] = RenderRecord(
        id="r1",
        timeline_id="main",
        output_path="renders/out.mp4",
        status="running",
    )

    assert render_status(project, "r1").status == "running"
    canceled = cancel_render(project, "r1")

    assert canceled.status == "canceled"
    assert render_status(project, "r1").status == "canceled"


def test_start_render_returns_running_and_cancel_terminates_process(tmp_path: Path) -> None:
    project_root, project = make_project(tmp_path)
    process = FakeProcess()

    def fake_popen(argv: list[str]) -> FakeProcess:
        process.argv = argv
        process.started.set()
        return process

    record = start_render(
        project,
        project_root,
        "main",
        "renders/out.mp4",
        popen=fake_popen,
    )

    assert record.status == "running"
    assert process.started.wait(timeout=1)

    canceled = cancel_render(project, record.id)

    assert canceled.status == "canceled"
    assert process.terminated
    assert process.finished.wait(timeout=1)
    assert render_status(project, record.id).status == "canceled"


class FakeProcess:
    def __init__(self) -> None:
        self.argv: list[str] = []
        self.returncode = 0
        self.stdout = ""
        self.stderr = ""
        self.started = Event()
        self.finished = Event()
        self.terminated = False

    def communicate(self) -> tuple[str, str]:
        self.finished.wait(timeout=1)
        return self.stdout, self.stderr

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15
        self.finished.set()


def make_project(tmp_path: Path) -> tuple[Path, CutGraphProject]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    media = project_root / "media" / "a.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"placeholder")
    project = CutGraphProject(
        settings=ProjectSettings(),
        assets={"clip_a": Asset(id="clip_a", path="media/a.mp4", media_type="video")},
        nodes={
            "clip1": Node(
                id="clip1",
                type="clip",
                asset_id="clip_a",
                duration=1.0,
            )
        },
        timelines={"main": Timeline(id="main", name="Main", node_ids=["clip1"])},
    )
    return project_root, project
