from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NodeType = Literal[
    "clip",
    "text_overlay",
    "image_overlay",
    "pip",
    "subtitles",
    "transition",
]


class ProjectSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    frame_rate: float = Field(default=30.0, gt=0)
    sample_rate: int = Field(default=48000, gt=0)
    render_dir: str = "renders"
    cache_dir: str = ".cutgraph/cache"


class Asset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    path: str
    media_type: str = "unknown"
    probe: dict[str, Any] = Field(default_factory=dict)


class Timeline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    node_ids: list[str] = Field(default_factory=list)


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: NodeType
    asset_id: str | None = None
    start: float = Field(default=0.0, ge=0)
    duration: float | None = Field(default=None, gt=0)
    source_start: float = Field(default=0.0, ge=0)
    properties: dict[str, Any] = Field(default_factory=dict)


class RenderRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    timeline_id: str
    output_path: str
    status: str = "planned"
    plan: dict[str, Any] | None = None
    error: str | None = None


class CutGraphProject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal["0.1"] = "0.1"
    settings: ProjectSettings
    assets: dict[str, Asset] = Field(default_factory=dict)
    timelines: dict[str, Timeline] = Field(default_factory=dict)
    nodes: dict[str, Node] = Field(default_factory=dict)
    renders: dict[str, RenderRecord] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self) -> CutGraphProject:
        for node in self.nodes.values():
            if node.asset_id is not None and node.asset_id not in self.assets:
                raise ValueError(
                    f"Node {node.id!r} references unknown asset {node.asset_id!r}"
                )

        for timeline in self.timelines.values():
            for node_id in timeline.node_ids:
                if node_id not in self.nodes:
                    raise ValueError(
                        f"Timeline {timeline.id!r} references unknown node {node_id!r}"
                    )

        for render in self.renders.values():
            if render.timeline_id not in self.timelines:
                raise ValueError(
                    f"Render {render.id!r} references unknown timeline "
                    f"{render.timeline_id!r}"
                )
        return self
