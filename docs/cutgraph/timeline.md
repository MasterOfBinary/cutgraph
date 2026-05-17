# CutGraph MVP And Future Timeline

## MVP Implemented

The current MVP includes:

- Python 3.12 `uv` package metadata.
- `.cutgraph.json` v0.1 schema for settings, assets, timelines, nodes, and renders.
- Project-root path allowlisting with render/cache directory policy.
- ffprobe-backed asset probing through argv arrays.
- Non-destructive timeline operations for create, add, trim, split, move, and delete.
- Render dry-run planning for trims, concat, overlays, PiP, subtitles, transitions, preview scaling, and final output paths.
- Render execution/job records with binary detection and clear failure state.
- CLI commands: `validate`, `probe`, `dry-run`, `render`, and `mcp`.
- FastMCP tool registration for project, asset, timeline, overlay, subtitle, transition, render, status/cancel, and OTIO export surfaces.
- OTIO-shaped JSON export without a mandatory OpenTimelineIO dependency.
- Tests for schema, path safety, media probing, timeline operations, render planning, render jobs, MCP registration, OTIO export, and FFmpeg-conditional integration checks.

## MVP Boundaries

CutGraph v0 does not try to match a full desktop NLE. It intentionally excludes:

- UI editing.
- CapCut/Premiere parity.
- Public raw FFmpeg execution.
- Arbitrary filesystem access outside the project root.
- In-place source media modification.

## Future Phase 1

- Add richer project creation/import CLI commands.
- Expand real-media integration tests with generated sample video/audio fixtures.
- Improve render planner compatibility checks for stream layouts, frame rates, pixel formats, and subtitle/font availability.
- Add proxy/cache generation under `.cutgraph/cache/`.
- Add stable JSON schemas for tool inputs and output receipts.

## Future Phase 2

- Support multi-track audio/video timelines.
- Add richer transition catalogs and per-transition compatibility diagnostics.
- Add background/asynchronous render process management with durable job state.
- Add thumbnails, waveform metadata, and low-resolution preview artifacts.
- Add import adapters for OTIO and common edit decision formats.

## Future Phase 3

- Add optional OpenTimelineIO-backed export/import when the extra dependency is installed.
- Add remote-safe MCP deployment guidance.
- Add project migration tooling for future `.cutgraph.json` versions.
- Add higher-level recipes for automated clip assembly, captions, and batch rendering.
