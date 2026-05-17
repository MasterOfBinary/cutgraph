# T001 Command Research Matrix

Checked: 2026-05-17

This note records the source-backed implementation decisions for CutGraph's MVP MCP tools and CLI commands. It distinguishes capabilities provided directly by FFmpeg, ffprobe, the MCP Python SDK, and OpenTimelineIO from project/timeline logic that CutGraph must own.

## Primary Sources

- MCP Python SDK README and docs: https://github.com/modelcontextprotocol/python-sdk and https://modelcontextprotocol.io/docs/develop/build-server. The current stable Python SDK is v1.x, exposes `FastMCP`, and registers tools with `@mcp.tool()` using type hints and docstrings.
- uv project docs: https://docs.astral.sh/uv/guides/projects/. uv manages Python projects with dependency metadata in `pyproject.toml` and runs project commands with `uv run`.
- FFmpeg command docs: https://ffmpeg.org/ffmpeg.html. Relevant options include `-ss`, `-t`, `-to`, `-filter_complex`, `-progress`, and `-nostdin`.
- FFmpeg filters docs: https://ffmpeg.org/ffmpeg-filters.html. Relevant filters include `trim`, `atrim`, `setpts`, `asetpts`, `concat`, `overlay`, `scale`, `drawtext`, `subtitles`, `xfade`, `acrossfade`, and `amix`.
- ffprobe docs: https://ffmpeg.org/ffprobe.html. ffprobe gathers stream/container metadata, supports JSON output, `-show_format`, `-show_streams`, `-show_entries`, `-count_frames`, and interval reads.
- OpenTimelineIO timeline docs: https://otio-core-documentation.readthedocs.io/en/latest/tutorials/otio-timeline-structure.html. OTIO timelines contain tracks, clips, transitions, gaps, media references, and source ranges.
- OpenTimelineIO adapter docs: https://opentimelineio.readthedocs.io/en/v0.12/tutorials/write-an-adapter.html. OTIO export uses timeline traversal and adapter write functions such as `write_to_file`/`write_to_string`.
- Pydantic docs: https://docs.pydantic.dev/latest/concepts/models/. Pydantic models provide validation and serialization through model fields and core schema.
- Typer docs: https://typer.tiangolo.com/. Typer builds CLI applications from Python type hints and supplies help/completion behavior.
- Rich docs: https://rich.readthedocs.io/. Rich provides terminal console/table output for readable CLI feedback.

## Dependency Decision Table

| Dependency | Decision | Why |
| --- | --- | --- |
| Python 3.12 | Required | Matches the charter and keeps modern typing available. |
| uv | Required | Source-backed project management via `pyproject.toml` and `uv run`. |
| MCP Python SDK (`mcp`) | Required | Official SDK includes `FastMCP`; use `mcp.server.fastmcp.FastMCP` and decorator-based tools. |
| Pydantic | Required | Best fit for `.cutgraph.json` schema validation, serialization, and stable structured tool returns. |
| Typer | Required | Fits `validate`, `probe`, `dry-run`, `render`, and `mcp` CLI commands with typed options. |
| Rich | Required | Use for human CLI status/errors/tables; JSON-ish MCP returns should remain plain structured data. |
| FFmpeg | Required system binary | Provides render execution, seeking, filtergraphs, overlays, subtitles, transitions, encoders, and progress output. |
| ffprobe | Required system binary | Provides media probing and stream/container metadata in machine-readable JSON. |
| OpenTimelineIO | Optional extra | Use only for export-first OTIO support. Core CutGraph must work when OTIO is not installed. |
| Shell execution | Rejected | Render plans must be argv arrays and executed with `subprocess` list arguments, never shell strings. |
| Raw public FFmpeg execution tool | Rejected | Security and explainability require scoped CutGraph operations and render plans. |

## MCP Tool Matrix

| Tool family | Public tools | Capability source | CutGraph responsibility |
| --- | --- | --- | --- |
| Project lifecycle | `create_project`, `open_project`, `validate_project`, `project_info` | Pydantic and local filesystem | Own schema, default settings, atomic `.cutgraph.json` writes, validation errors, project-root safety, and versioning. FFmpeg is not involved. |
| Asset/probe | `add_asset`, `probe_asset`, `list_assets`, `remove_asset` | ffprobe for metadata | Own asset IDs, path allowlisting, duplicate/update semantics, cached probe data, actionable missing `ffprobe` errors, and JSON normalization. |
| Timeline lifecycle | `create_timeline`, `list_timelines`, `get_timeline`, `delete_timeline` | CutGraph data model | Own all behavior. FFmpeg has no project/timeline object model. |
| Clip edits | `add_clip`, `trim_clip`, `split_clip`, `move_clip`, `delete_clip` | FFmpeg can trim/render media, but not edit CutGraph project state | Store non-destructive node ranges and order. `trim`/`atrim` prove render feasibility; CutGraph must validate ranges and mutate `.cutgraph.json`. Split is a data operation creating two clip nodes. |
| Ordering/concat | `reorder_clip`, `set_clip_timing`, timeline render sequencing | FFmpeg `concat` filter can join streams | CutGraph must compile node order into concat-compatible filtergraphs, normalize timestamps with `setpts`/`asetpts`, and handle stream compatibility. |
| Text overlays | `add_text_overlay`, `update_overlay`, `remove_overlay` | FFmpeg `drawtext` | CutGraph owns overlay node schema, escaping, timing windows, font/style defaults, and docs about build-dependent drawtext font features. |
| Image/video overlays | `add_overlay`, `add_pip`, `update_overlay` | FFmpeg `overlay` and `scale` | CutGraph owns layer order, x/y/size semantics, timeline timing, media path validation, alpha behavior, and filtergraph construction. |
| Subtitles | `add_subtitle_track`, `add_subtitle_file`, `remove_subtitles` | FFmpeg `subtitles`/`ass` filters | CutGraph owns subtitle asset registration and style metadata. Rendering depends on an FFmpeg build with libass for the `subtitles` filter. |
| Transitions | `add_transition`, `remove_transition` | FFmpeg `xfade` for video and `acrossfade` for audio | CutGraph owns transition placement, adjacent clip validation, duration limits, compatibility normalization, and fallback/deferral if a transition cannot be made safe. |
| Preview/final render planning | `plan_render`, `dry_run_render` | FFmpeg command/filtergraph grammar | CutGraph owns deterministic render plans, argv arrays, explanations, output path policy, codec presets, preview scaling, and no-shell guarantees. |
| Render execution | `start_render`, `render_status`, `cancel_render` | FFmpeg process and `-progress` output | CutGraph owns local job registry, process lifecycle, progress parsing, cancellation, stdout/stderr capture, and output safety. |
| Render listing | `list_renders`, `get_render` | CutGraph data model | Own render records in `.cutgraph.json`, statuses, output metadata, and errors. |
| OTIO export | `export_otio` | Optional OpenTimelineIO | CutGraph owns conversion from internal timelines to OTIO tracks/clips/source ranges and optional dependency errors. |

## CLI Command Matrix

| Command | Capability source | CutGraph responsibility |
| --- | --- | --- |
| `cutgraph validate PROJECT` | Pydantic/local filesystem | Load `.cutgraph.json`, enforce schema/path rules, print human output, return nonzero on invalid project. |
| `cutgraph probe PROJECT MEDIA` | ffprobe | Validate media path, run ffprobe with JSON output, store or print normalized metadata, report missing binary clearly. |
| `cutgraph dry-run PROJECT TIMELINE` | FFmpeg planner only | Compile project state into an explainable argv plan without executing FFmpeg. |
| `cutgraph render PROJECT TIMELINE OUTPUT` | FFmpeg | Plan and run FFmpeg via argv list, ensure output stays under `renders/`, track status, and surface progress/errors. |
| `cutgraph mcp` | MCP Python SDK FastMCP | Start the local MCP server using official FastMCP patterns. |

## Operation Notes

- Trim: FFmpeg supports both video `trim` and audio `atrim`, plus command-level `-ss`/`-t`/`-to`. CutGraph should treat clip trim as metadata mutation and use filter-level trim/atrim plus timestamp reset in render plans for precise, non-destructive output.
- Split: FFmpeg does not own project split semantics. CutGraph should create two clip nodes with adjusted `source_start`/`duration`.
- Move/delete/reorder: These are CutGraph timeline mutations. Rendering later maps the resulting ordered clips into concat/filtergraph steps.
- Concat: FFmpeg `concat` joins synchronized segments with the same number of stream types. CutGraph must normalize durations, timestamps, resolution/pixel format where needed, and make unsupported combinations explicit.
- Overlays and PiP: FFmpeg supports overlaying one stream on another and scaling. CutGraph must build layered filtergraphs and validate overlay media/timing.
- Text overlays: FFmpeg `drawtext` is suitable, but its richer font behavior depends on FFmpeg build flags. CutGraph should start with conservative style fields and escaping.
- Subtitles: FFmpeg `subtitles` can burn subtitle files when FFmpeg is built with libass. CutGraph must detect/render errors cleanly and document the binary requirement.
- Transitions: FFmpeg `xfade` requires constant frame-rate inputs with the same resolution, pixel format, frame rate, and timebase. CutGraph should normalize or reject with a useful planner error. Audio crossfades use `acrossfade`.
- Preview renders: Use the same planner as final render with constrained resolution/codec/output naming. Preview is a render preset, not a separate semantics engine.
- Render status/cancel: FFmpeg exposes program-friendly progress via `-progress`; CutGraph should add `-nostdin`, read progress lines, store job state, and terminate the process for cancellation.
- OTIO export: OTIO source ranges map well to CutGraph clip source ranges. Transitions/gaps can be represented, but advanced overlays/PiP may need metadata or scoped deferral in v0.

## Risks For Judge

- MCP SDK API drift: use the stable v1.x import path and add MCP smoke tests that verify tools are registered. Avoid advanced SDK features for v0.
- FFmpeg build variance: `drawtext` and `subtitles` depend on build options. Tests should mock planner output and make real-media integration tests skip or report clearly when unsupported.
- Transition compatibility: `xfade` constraints mean CutGraph must either normalize inputs in the planner or reject transitions with explicit reasons.
- Escaping filter arguments: text, subtitle paths, and filtergraph expressions require careful escaping. Prefer generated filter strings from structured nodes and keep all process execution as argv.
- Path safety: every user-supplied media/output path must resolve under the project root, with outputs limited to `renders/` and cache/proxy files to `.cutgraph/cache/`.
- OTIO optional boundary: core package and tests must pass without OTIO installed; export should return actionable install guidance.
