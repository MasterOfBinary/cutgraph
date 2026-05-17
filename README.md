# CutGraph

CutGraph is a local, `uv`-managed Python 3.12 package for non-destructive video editing automation. A `.cutgraph.json` file is the editable project source of truth; source media stays untouched; CLI and MCP tools mutate structured project data; rendering compiles that data into explainable FFmpeg argv plans.

## Commands

```bash
uv run cutgraph validate /path/to/project
uv run cutgraph probe /path/to/project media/clip.mp4
uv run cutgraph dry-run /path/to/project main renders/out.mp4
uv run cutgraph render /path/to/project main renders/out.mp4
uv run cutgraph mcp
```

FFmpeg and ffprobe must be installed separately for real probing and rendering. The regular Homebrew `ffmpeg` package can render core trim/concat/overlay timelines, but text overlays and burned subtitles require an FFmpeg build with `drawtext` and `subtitles` filters. On macOS, `ffmpeg-full` provides those filters:

```bash
brew install ffmpeg-full

# If regular ffmpeg is still linked first, either link ffmpeg-full:
brew unlink ffmpeg
brew link ffmpeg-full

# Or put ffmpeg-full first only for this shell:
export PATH="/opt/homebrew/opt/ffmpeg-full/bin:$PATH"

ffmpeg -hide_banner -filters | grep -E 'drawtext|subtitles|overlay|xfade|acrossfade|concat|atrim|trim'
```

`ffmpeg -version` should show a prefix under `/opt/homebrew/Cellar/ffmpeg-full/...` when testing the full text/subtitle render path.

## Documentation

- [Developer guide](docs/cutgraph/developer.md)
- [User guide](docs/cutgraph/user.md)
- [MVP and future timeline](docs/cutgraph/timeline.md)
- [Source-backed command research](docs/goals/cutgraph-timeline-mcp/notes/T001-command-research.md)
