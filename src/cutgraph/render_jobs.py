from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable, Protocol

from .binaries import MissingBinaryError, require_binary
from .render import plan_render
from .schema import CutGraphProject, RenderRecord
from .store import save_project


class RenderExecutionError(RuntimeError):
    """Raised when a render job cannot be started or completes unsuccessfully."""


RenderRunner = Callable[[list[str]], CompletedProcess[str]]


class RenderProcess(Protocol):
    returncode: int | None

    def communicate(self) -> tuple[str, str]:
        ...

    def terminate(self) -> None:
        ...


RenderPopen = Callable[[list[str]], RenderProcess]


@dataclass
class _ActiveRender:
    record: RenderRecord
    process: RenderProcess | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


_ACTIVE_RENDERS: dict[str, _ActiveRender] = {}
_ACTIVE_LOCK = threading.Lock()


def run_render(
    project: CutGraphProject,
    project_root: Path | str,
    timeline_id: str,
    output_path: Path | str,
    *,
    preset: str = "final",
    render_id: str | None = None,
    runner: RenderRunner | None = None,
) -> RenderRecord:
    plan = plan_render(project, project_root, timeline_id, output_path, preset=preset)

    record = RenderRecord(
        id=render_id or _next_render_id(project),
        timeline_id=timeline_id,
        output_path=plan.output_path,
        status="running",
        plan=plan.model_dump(mode="json"),
    )
    project.renders[record.id] = record

    try:
        completed = (runner or _run_ffmpeg)(plan.argv)
    except FileNotFoundError as exc:
        message = "FFmpeg was not found. Install FFmpeg/ffprobe and ensure ffmpeg is on PATH."
        record.status = "failed"
        record.error = message
        raise RenderExecutionError(message) from exc
    except MissingBinaryError as exc:
        record.status = "failed"
        record.error = str(exc)
        raise RenderExecutionError(str(exc)) from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "unknown FFmpeg error"
        record.status = "failed"
        record.error = detail
        raise RenderExecutionError(detail)

    record.status = "completed"
    return record


def start_render(
    project: CutGraphProject,
    project_root: Path | str,
    timeline_id: str,
    output_path: Path | str,
    *,
    preset: str = "final",
    render_id: str | None = None,
    popen: RenderPopen | None = None,
) -> RenderRecord:
    plan = plan_render(project, project_root, timeline_id, output_path, preset=preset)
    record = RenderRecord(
        id=render_id or _next_render_id(project),
        timeline_id=timeline_id,
        output_path=plan.output_path,
        status="running",
        plan=plan.model_dump(mode="json"),
    )
    project.renders[record.id] = record
    active = _ActiveRender(record=record)
    with _ACTIVE_LOCK:
        _ACTIVE_RENDERS[record.id] = active

    thread = threading.Thread(
        target=_run_render_in_background,
        args=(project, Path(project_root), active, plan.argv, popen or _popen_ffmpeg),
        daemon=True,
    )
    thread.start()
    return record


def render_status(project: CutGraphProject, render_id: str) -> RenderRecord:
    try:
        return project.renders[render_id]
    except KeyError as exc:
        raise RenderExecutionError(f"Unknown render {render_id!r}") from exc


def cancel_render(project: CutGraphProject, render_id: str) -> RenderRecord:
    record = render_status(project, render_id)
    if record.status in {"completed", "failed", "canceled"}:
        return record
    record.status = "canceled"
    with _ACTIVE_LOCK:
        active = _ACTIVE_RENDERS.get(render_id)
    if active is not None:
        active.record.status = "canceled"
        with active.lock:
            process = active.process
        if process is not None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
    return record


def _run_ffmpeg(argv: list[str]) -> CompletedProcess[str]:
    require_binary(argv[0])
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def _popen_ffmpeg(argv: list[str]) -> RenderProcess:
    require_binary(argv[0])
    return subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _run_render_in_background(
    project: CutGraphProject,
    project_root: Path,
    active: _ActiveRender,
    argv: list[str],
    popen: RenderPopen,
) -> None:
    try:
        process = popen(argv)
        with active.lock:
            active.process = process
        if active.record.status == "canceled":
            try:
                process.terminate()
            except ProcessLookupError:
                pass
        _stdout, stderr = process.communicate()
    except FileNotFoundError:
        if active.record.status != "canceled":
            active.record.status = "failed"
            active.record.error = "FFmpeg was not found. Install FFmpeg/ffprobe and ensure ffmpeg is on PATH."
    except MissingBinaryError as exc:
        if active.record.status != "canceled":
            active.record.status = "failed"
            active.record.error = str(exc)
    else:
        if active.record.status == "canceled":
            active.record.error = None
        elif process.returncode != 0:
            active.record.status = "failed"
            active.record.error = stderr.strip() or "unknown FFmpeg error"
        else:
            active.record.status = "completed"
    finally:
        with _ACTIVE_LOCK:
            _ACTIVE_RENDERS.pop(active.record.id, None)
        save_project(project_root, project)


def _next_render_id(project: CutGraphProject) -> str:
    index = len(project.renders) + 1
    candidate = f"render_{index}"
    while candidate in project.renders:
        index += 1
        candidate = f"render_{index}"
    return candidate
