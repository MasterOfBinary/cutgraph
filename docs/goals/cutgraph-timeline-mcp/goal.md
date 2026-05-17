# CutGraph Timeline MCP

## Objective

Build CutGraph as a Python 3.12, `uv`-managed local MCP server for non-destructive video editing, where `.cutgraph.json` is the Git-friendly source of truth, source media stays untouched, MCP tools mutate structured project data, and rendering compiles project state into explainable FFmpeg/ffprobe operations.

## Original Request

User asked to build the CutGraph Timeline MCP plan, with in-depth research into how to implement each command and whether capabilities are provided by FFmpeg/ffprobe or must be developed in CutGraph; also write separate developer docs and user docs, plus documentation of the MVP and future-phase timeline.

## Intake Summary

- Input shape: `existing_plan`
- Audience: local developers and MCP users who want scriptable non-destructive video editing without a UI.
- Authority: `requested`
- Proof type: `test`
- Completion proof: a Python 3.12 `uv` package exists with the requested MCP tools and CLI commands, source-backed implementation research is captured, developer/user/timeline docs are separate, and the test suite plus FFmpeg-conditional integration checks pass or skip with clear reasons.
- Likely misfire: building a plausible project skeleton or arbitrary FFmpeg wrapper without validating the actual command feasibility, security model, docs, and non-destructive project semantics requested by the user.
- Blind spots considered: FFmpeg feature coverage versus custom timeline logic, path safety, render-plan explainability, optional OTIO dependency boundaries, MCP SDK API drift, real-media integration tests, cancellation semantics, and docs staying distinct for developers and users.
- Existing plan facts:
  - Python package under `src/cutgraph/`.
  - Python 3.12 and `uv`.
  - Runtime dependencies: MCP Python SDK, Pydantic, Typer, Rich, optional OpenTimelineIO.
  - `.cutgraph.json` v0.1 contains `settings`, `assets`, `timelines`, `nodes`, and `renders`.
  - Project-root path allowlisting; outputs under `renders/`; cache/proxies under `.cutgraph/cache/`.
  - Public MCP tools include project lifecycle, assets/probing, timeline operations, transitions/overlays/PiP/subtitles, rendering, render status/cancel, and OTIO export.
  - CLI commands include `validate`, `probe`, `dry-run`, `render`, and `mcp`.
  - Render planner emits argv arrays, never shell strings, and returns explainable render plans before execution.
  - v0 requires system-installed FFmpeg/ffprobe and no public raw `execute_ffmpeg`.
  - No UI, no CapCut/Premiere parity in v0.
  - References to validate include MCP Python SDK/docs, FFmpeg docs/filters, and OpenTimelineIO timeline structure docs.

## Goal Kind

`existing_plan`

## Current Tranche

Validate and implement the MVP as successive safe verified slices: source-backed command research, plan validation, core package/schema/store/security, media probing, timeline operations, render planning/execution, MCP/CLI exposure, OTIO export, documentation, and final verification. Continue until the full requested build is complete, not merely until a scaffold or research note exists.

## Non-Negotiable Constraints

- Use Python 3.12 and `uv` project conventions.
- Keep source media untouched; all editing is non-destructive project data mutation.
- `.cutgraph.json` is the project source of truth.
- Use official MCP Python SDK/FastMCP patterns for tool exposure.
- Use system FFmpeg/ffprobe for real probing and rendering; produce actionable missing-binary errors.
- Do not expose a public raw `execute_ffmpeg` tool.
- Render plans must be argv arrays, never shell strings.
- Enforce project-root path allowlisting.
- Keep developer docs, user docs, and MVP/future timeline docs separate.
- Use source-backed research for every public command/tool family before implementation decisions are locked.

## Stop Rule

Stop only when a final audit proves the full original outcome is complete.

Do not stop after planning, discovery, or Judge selection if the user asked for working software and a safe Worker task can be activated.

Do not stop after a single verified Worker package when the broader owner outcome still has safe local follow-up work. Advance the board to the next highest-leverage safe Worker package and continue unless a phase, risk, rejected-verification, ambiguity, or final-completion review is due.

Do not create one Worker/Judge pair per repeated file, command, or helper. Put repeated same-shape work into one Worker package and review the package as a whole.

Do not stop because a slice needs owner input, credentials, production access, destructive operations, or policy decisions. Mark that exact slice blocked with a receipt, create the smallest safe follow-up or workaround task, and continue all local, non-destructive work that can still move the goal toward the full outcome.

## Slice Sizing

Safe means bounded, explicit, verified, and reversible. It does not mean tiny.

A good task is the largest safe useful slice.

Small is not the goal. Useful is the goal.

A Worker should finish the whole assigned slice. A Judge should judge the whole assigned slice. A PM should reorient the board when tasks are safe but not moving the outcome.

Tiny tasks are allowed when the failure is isolated, the risk is high, the scope is unknown, or the tiny task unlocks a larger slice. Tiny tasks are bad when they keep happening, do not change behavior, only add wrappers/contracts/proof files, or avoid the real milestone.

## Canonical Board

Machine truth lives at:

`docs/goals/cutgraph-timeline-mcp/state.yaml`

If this charter and `state.yaml` disagree, `state.yaml` wins for task status, active task, receipts, verification freshness, and completion truth.

## Run Command

```text
/goal Follow docs/goals/cutgraph-timeline-mcp/goal.md.
```

## PM Loop

On every `/goal` continuation:

1. Read this charter.
2. Read `state.yaml`.
3. Run the bundled GoalBuddy update checker when available and mention a newer version without blocking.
4. Re-check the intake: original request, input shape, authority, proof, blind spots, existing plan facts, and likely misfire.
5. Work only on the active board task.
6. Assign Scout, Judge, Worker, or PM according to the task.
7. Write a compact task receipt.
8. Update the board.
9. If safe local work remains, choose the next largest reversible Worker package and continue unless blocked.
10. If a problem, suggestion, or follow-up should become a repo artifact, create an approved issue/PR or ask the operator whether to create one.
11. Review at phase, risk, rejected-verification, ambiguity, or final-completion boundaries; do not review every small Worker by habit.
12. Finish only with a Judge/PM audit receipt that maps receipts and verification back to the original user outcome and records `full_outcome_complete: true`.
