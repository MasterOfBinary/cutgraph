from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from cutgraph.media import ProbeError, probe_asset
from cutgraph.schema import CutGraphProject, ProjectSettings


def test_probe_asset_runs_ffprobe_as_argv_and_stores_metadata(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    media = project_root / "media" / "clip.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"source media remains untouched")
    calls: list[list[str]] = []

    def fake_run(argv: list[str]) -> CompletedProcess[str]:
        calls.append(argv)
        return CompletedProcess(
            argv,
            0,
            stdout=json.dumps(
                {
                    "format": {"duration": "12.5", "format_name": "mov,mp4"},
                    "streams": [
                        {
                            "codec_type": "video",
                            "width": 1920,
                            "height": 1080,
                            "avg_frame_rate": "30/1",
                        }
                    ],
                }
            ),
            stderr="",
        )

    project = CutGraphProject(settings=ProjectSettings())
    asset = probe_asset(project, project_root, "media/clip.mp4", runner=fake_run)

    assert calls == [
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(media.resolve()),
        ]
    ]
    assert asset.id == "clip"
    assert asset.probe["format"]["duration"] == "12.5"
    assert project.assets["clip"] == asset
    assert media.read_bytes() == b"source media remains untouched"


def test_probe_asset_generates_unique_default_asset_ids(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    first = project_root / "media" / "clip.mp4"
    second = project_root / "other" / "clip.mov"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    def fake_run(argv: list[str]) -> CompletedProcess[str]:
        return CompletedProcess(
            argv,
            0,
            stdout=json.dumps({"streams": [{"codec_type": "video"}]}),
            stderr="",
        )

    project = CutGraphProject(settings=ProjectSettings())

    first_asset = probe_asset(project, project_root, "media/clip.mp4", runner=fake_run)
    second_asset = probe_asset(project, project_root, "other/clip.mov", runner=fake_run)

    assert first_asset.id == "clip"
    assert second_asset.id == "clip_2"
    assert set(project.assets) == {"clip", "clip_2"}


def test_probe_asset_reports_missing_ffprobe(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    media = project_root / "media" / "clip.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"not real video")

    def missing_ffprobe(_argv: list[str]) -> CompletedProcess[str]:
        raise FileNotFoundError("ffprobe")

    with pytest.raises(ProbeError, match="ffprobe"):
        probe_asset(
            CutGraphProject(settings=ProjectSettings()),
            project_root,
            "media/clip.mp4",
            runner=missing_ffprobe,
        )
