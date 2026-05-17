# CutGraph User Guide

## What CutGraph Does

CutGraph lets you describe local video edits in a `.cutgraph.json` project file, then preview or render those edits with FFmpeg. It is designed for automation through a CLI or MCP tools, not for manual timeline editing in a GUI.

Source media files are read-only inputs. Edits such as trim, split, move, overlays, subtitles, transitions, and render settings are stored as structured project data.

## Requirements

- Python 3.12
- uv
- FFmpeg and ffprobe on `PATH` for real probing and rendering

The regular Homebrew `ffmpeg` formula is enough for core trim, concat, transition, and overlay renders. Text overlays and burned subtitles need an FFmpeg build with `drawtext` and `subtitles`; on macOS, install and activate `ffmpeg-full`:

```bash
brew install ffmpeg-full
brew unlink ffmpeg
brew link ffmpeg-full

ffmpeg -version
ffmpeg -hide_banner -filters | grep -E 'drawtext|subtitles|overlay|xfade|acrossfade|concat|atrim|trim'
```

If you do not want to relink Homebrew packages, put `ffmpeg-full` first for the current shell:

```bash
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"
```

## CLI Commands

Validate a project:

```bash
uv run cutgraph validate /path/to/project
```

Probe media and register it as an asset:

```bash
uv run cutgraph probe /path/to/project media/clip.mp4
```

Compile a render plan without running FFmpeg:

```bash
uv run cutgraph dry-run /path/to/project main renders/out.mp4
```

Render a timeline:

```bash
uv run cutgraph render /path/to/project main renders/out.mp4
```

Run the MCP server:

```bash
uv run cutgraph mcp
```

## MCP Workflow

Use MCP tools to create projects, add/probe assets, create timelines, add and edit clips, add overlays/PiP/subtitles/transitions, plan renders, start renders, check render status, cancel queued/running records, and export OTIO JSON.

The core tool groups are:

- Project: `create_project`, `validate_project`, `project_info`
- Asset: `probe_asset`
- Timeline: `create_timeline`, `add_clip`, `trim_clip`, `split_clip`, `move_clip`, `delete_clip`
- Visual layers: `add_text_overlay`, `add_overlay`, `add_pip`, `add_subtitles`, `add_transition`
- Render: `plan_render`, `start_render`, `render_status`, `cancel_render`
- Interchange: `export_otio`

## Project Safety

CutGraph enforces project-root path boundaries. Media paths must be under the project root. Render outputs must be under `renders/`. Cache/proxy paths belong under `.cutgraph/cache/`.

If FFmpeg or ffprobe is missing, CutGraph reports an actionable install/PATH error instead of silently failing.

## Current Limitations

- No graphical editor.
- No raw public `execute_ffmpeg` tool.
- Render planning assumes normal audio/video streams for MVP plans.
- FFmpeg build options affect `drawtext` and `subtitles` support; use `ffmpeg-full` or an equivalent build for those features.
- OTIO export is JSON-focused in the core install.
