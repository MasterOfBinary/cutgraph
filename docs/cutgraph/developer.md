# CutGraph Developer Guide

## Architecture

CutGraph keeps editing state in `.cutgraph.json`. The project schema is implemented with Pydantic models in `src/cutgraph/schema.py` and contains:

- `settings`: render/cache directories plus default media settings.
- `assets`: source media references and optional ffprobe metadata.
- `timelines`: ordered node references.
- `nodes`: non-destructive clip, overlay, subtitle, transition, and render-planning objects.
- `renders`: render job records and stored render plans.

Source media is never edited in place. Timeline operations in `src/cutgraph/timeline.py` mutate project nodes and timeline order only.

## Path Safety

`src/cutgraph/security.py` resolves user paths through `ProjectPaths`. Media paths must resolve under the project root. Render outputs must resolve under `renders/`, and cache paths must resolve under `.cutgraph/cache/`. Symlink escapes are rejected because paths are resolved before boundary checks.

## Media And Rendering

`src/cutgraph/media.py` runs ffprobe as an argv array:

```text
ffprobe -v error -show_format -show_streams -of json <media>
```

`src/cutgraph/render.py` compiles timelines into a `RenderPlan` with:

- `inputs`: resolved source paths.
- `filtergraph`: FFmpeg filter graph text.
- `argv`: an executable argument array, never a shell string.
- `explanations`: human-readable planning notes.

The planner currently covers clip trim/atrim, timestamp reset, concat, text overlays, image overlays, PiP, subtitles, video/audio crossfades, preview scaling, and final render output paths.

`src/cutgraph/render_jobs.py` supports blocking CLI renders with `subprocess.run(argv, ...)` and MCP background renders with `subprocess.Popen(argv, ...)`, records job state, and terminates active processes on cancel.

For full local render verification on macOS, ensure `ffmpeg-full` is the active FFmpeg binary. The regular Homebrew `ffmpeg` package may not include `drawtext` or `subtitles`.

```bash
brew install ffmpeg-full
brew unlink ffmpeg
brew link ffmpeg-full
ffmpeg -version
ffmpeg -hide_banner -filters | grep -E 'drawtext|subtitles|overlay|xfade|acrossfade|concat|atrim|trim'
```

If both `ffmpeg` and `ffmpeg-full` are installed but regular `ffmpeg` remains linked, run integration tests with:

```bash
PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH" uv run pytest tests -m integration
```

## MCP Server

`src/cutgraph/mcp_server.py` uses the official MCP Python SDK `FastMCP` server. Registered tools cover project lifecycle, probing, timeline edits, overlays, PiP, subtitles, transitions, render planning/execution, render status/cancel, and OTIO export.

Run locally with:

```bash
uv run cutgraph mcp
```

## OTIO Export

`src/cutgraph/otio_export.py` exports an OTIO-shaped JSON timeline without requiring OpenTimelineIO at import time. This keeps the core package usable without optional editor interchange dependencies.

## Verification

Run:

```bash
uv run pytest tests
uv run pytest tests -m integration
```

Integration tests skip when FFmpeg/ffprobe are not installed on `PATH`. Full text/subtitle integration tests skip unless the active FFmpeg exposes `drawtext`, `subtitles`, `overlay`, `xfade`, and `acrossfade`.

The source-backed implementation research for command decisions lives in `docs/goals/cutgraph-timeline-mcp/notes/T001-command-research.md`.
