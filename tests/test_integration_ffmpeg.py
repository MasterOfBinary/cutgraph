import shutil
import subprocess
from pathlib import Path

import pytest

from cutgraph.media import probe_asset
from cutgraph.render_jobs import run_render
from cutgraph.schema import Node
from cutgraph.store import create_project
from cutgraph.timeline import add_clip, create_timeline


@pytest.mark.integration
def test_ffmpeg_and_ffprobe_version_commands_or_skip() -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/ffprobe are not installed on PATH")

    subprocess.run([ffmpeg, "-version"], check=True, capture_output=True, text=True)
    subprocess.run([ffprobe, "-version"], check=True, capture_output=True, text=True)


@pytest.mark.integration
def test_cutgraph_renders_generated_concat_video_or_skip(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/ffprobe are not installed on PATH")

    project_root = tmp_path / "project"
    media_dir = project_root / "media"
    media_dir.mkdir(parents=True)
    renders_dir = project_root / "renders"
    renders_dir.mkdir()
    first = media_dir / "a.mp4"
    second = media_dir / "b.mp4"

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "2",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(first),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "smptebars=size=320x180:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=660:sample_rate=48000",
            "-t",
            "2",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(second),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    project = create_project(project_root)
    probe_asset(project, project_root, "media/a.mp4", asset_id="a")
    probe_asset(project, project_root, "media/b.mp4", asset_id="b")
    create_timeline(project, "main", "Main")
    add_clip(project, "main", "a", node_id="clip_a", duration=1.5)
    add_clip(project, "main", "b", node_id="clip_b", duration=1.5)

    record = run_render(project, project_root, "main", "renders/out.mp4")

    assert record.status == "completed"
    output = renders_dir / "out.mp4"
    assert output.stat().st_size > 0
    probe = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert float(probe.stdout.strip()) >= 2.9


@pytest.mark.integration
def test_cutgraph_renders_generated_overlay_subtitle_timeline_or_skip(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/ffprobe are not installed on PATH")
    filters = _ffmpeg_filters(ffmpeg)
    missing = {
        "drawtext",
        "subtitles",
        "overlay",
        "xfade",
        "acrossfade",
    }.difference(filters)
    if missing:
        pytest.skip(f"FFmpeg is missing required filters: {', '.join(sorted(missing))}")

    project_root = tmp_path / "project"
    media_dir = project_root / "media"
    media_dir.mkdir(parents=True)
    renders_dir = project_root / "renders"
    renders_dir.mkdir()
    first = media_dir / "a.mp4"
    second = media_dir / "b.mp4"
    pip = media_dir / "pip.mp4"
    logo = media_dir / "logo.png"
    captions = media_dir / "captions.srt"

    _generate_video(ffmpeg, first, "testsrc2=size=320x180:rate=30", 440)
    _generate_video(ffmpeg, second, "smptebars=size=320x180:rate=30", 660)
    _generate_video(ffmpeg, pip, "testsrc=size=160x90:rate=30", 880)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=80x40",
            "-frames:v",
            "1",
            str(logo),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    captions.write_text(
        "1\n00:00:00,500 --> 00:00:02,500\nHello CutGraph\n",
        encoding="utf-8",
    )

    project = create_project(project_root)
    for asset_id, relative in [
        ("a", "media/a.mp4"),
        ("b", "media/b.mp4"),
        ("pip", "media/pip.mp4"),
        ("logo", "media/logo.png"),
        ("subs", "media/captions.srt"),
    ]:
        probe_asset(project, project_root, relative, asset_id=asset_id)
    create_timeline(project, "main", "Main")
    add_clip(project, "main", "a", node_id="clip_a", duration=2.0)
    add_clip(project, "main", "b", node_id="clip_b", duration=2.0)
    project.nodes["fade"] = Node(
        id="fade",
        type="transition",
        properties={"kind": "fade", "duration": 0.5},
    )
    project.nodes["title"] = Node(
        id="title",
        type="text_overlay",
        properties={"text": "Hello CutGraph", "x": 12, "y": 12, "start": 0, "duration": 3},
    )
    project.nodes["logo_overlay"] = Node(
        id="logo_overlay",
        type="image_overlay",
        asset_id="logo",
        properties={"x": 12, "y": 60, "width": 60, "start": 0, "duration": 3},
    )
    project.nodes["pip_overlay"] = Node(
        id="pip_overlay",
        type="pip",
        asset_id="pip",
        properties={"x": 190, "y": 90, "width": 100, "start": 0.5, "duration": 2},
    )
    project.nodes["subtitles"] = Node(id="subtitles", type="subtitles", asset_id="subs")
    project.timelines["main"].node_ids = [
        "clip_a",
        "fade",
        "clip_b",
        "title",
        "logo_overlay",
        "pip_overlay",
        "subtitles",
    ]

    record = run_render(project, project_root, "main", "renders/full.mp4")

    assert record.status == "completed"
    output = renders_dir / "full.mp4"
    assert output.stat().st_size > 0
    probe = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert float(probe.stdout.strip()) >= 3.4


def _generate_video(ffmpeg: str, output: Path, source: str, frequency: int) -> None:
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            source,
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:sample_rate=48000",
            "-t",
            "3",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _ffmpeg_filters(ffmpeg: str) -> set[str]:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"],
        check=True,
        capture_output=True,
        text=True,
    )
    names: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and "->" in parts[2]:
            names.add(parts[1])
    return names
