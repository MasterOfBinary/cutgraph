from __future__ import annotations

import json
import re
import subprocess
from json import JSONDecodeError
from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable

from .schema import Asset, CutGraphProject
from .security import ProjectPaths


class ProbeError(RuntimeError):
    """Raised when ffprobe cannot produce usable media metadata."""


ProbeRunner = Callable[[list[str]], CompletedProcess[str]]


def probe_asset(
    project: CutGraphProject,
    project_root: Path | str,
    media_path: Path | str,
    *,
    asset_id: str | None = None,
    runner: ProbeRunner | None = None,
    ffprobe: str = "ffprobe",
) -> Asset:
    paths = ProjectPaths(project_root)
    resolved = paths.resolve_project_path(media_path)
    argv = [
        ffprobe,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(resolved),
    ]

    try:
        completed = (runner or _run_ffprobe)(argv)
    except FileNotFoundError as exc:
        raise ProbeError(
            "ffprobe was not found. Install FFmpeg/ffprobe and ensure it is on PATH."
        ) from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "unknown ffprobe error"
        raise ProbeError(f"ffprobe failed for {media_path!s}: {detail}")

    try:
        probe = json.loads(completed.stdout)
    except JSONDecodeError as exc:
        raise ProbeError(f"ffprobe returned invalid JSON for {media_path!s}") from exc

    relative_path = resolved.relative_to(paths.project_root).as_posix()
    asset = Asset(
        id=asset_id or _unique_asset_id(project, _default_asset_id(resolved)),
        path=relative_path,
        media_type=_detect_media_type(probe),
        probe=probe,
    )
    project.assets[asset.id] = asset
    return asset


def _run_ffprobe(argv: list[str]) -> CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def _default_asset_id(path: Path) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_]+", "_", path.stem).strip("_").lower()
    return stem or "asset"


def _unique_asset_id(project: CutGraphProject, prefix: str) -> str:
    candidate = prefix
    suffix = 2
    while candidate in project.assets:
        candidate = f"{prefix}_{suffix}"
        suffix += 1
    return candidate


def _detect_media_type(probe: dict[str, object]) -> str:
    streams = probe.get("streams")
    if not isinstance(streams, list):
        return "unknown"
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        codec_type = stream.get("codec_type")
        if codec_type in {"video", "audio", "subtitle", "image"}:
            return str(codec_type)
    return "unknown"
