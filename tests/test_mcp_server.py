import asyncio

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from cutgraph.mcp_server import REQUIRED_TOOL_NAMES, create_server
from cutgraph.store import load_project


def test_mcp_server_registers_required_tools() -> None:
    server = create_server()

    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}

    assert set(REQUIRED_TOOL_NAMES).issubset(names)


def test_mcp_tool_invocation_mutates_project(tmp_path) -> None:
    server = create_server()

    _call_tool(server, "create_project", {"project_root": str(tmp_path)})
    timeline = _call_tool(
        server,
        "create_timeline",
        {"project_root": str(tmp_path), "timeline_id": "main", "name": "Main"},
    )

    project = load_project(tmp_path)
    assert timeline["id"] == "main"
    assert "main" in project.timelines


def test_mcp_overlay_without_duration_does_not_store_forever_sentinel(tmp_path) -> None:
    server = create_server()
    _call_tool(server, "create_project", {"project_root": str(tmp_path)})
    _call_tool(
        server,
        "create_timeline",
        {"project_root": str(tmp_path), "timeline_id": "main", "name": "Main"},
    )

    overlay = _call_tool(
        server,
        "add_text_overlay",
        {
            "project_root": str(tmp_path),
            "timeline_id": "main",
            "node_id": "title",
            "text": "Title",
        },
    )

    assert "duration" not in overlay["properties"]


def test_mcp_append_node_reports_unknown_timeline_as_value_error(tmp_path) -> None:
    server = create_server()
    _call_tool(server, "create_project", {"project_root": str(tmp_path)})

    with pytest.raises(ToolError, match="Unknown timeline"):
        _call_tool(
            server,
            "add_text_overlay",
            {
                "project_root": str(tmp_path),
                "timeline_id": "missing",
                "node_id": "title",
                "text": "Title",
            },
        )


def test_mcp_add_transition_rejects_out_of_bounds_index(tmp_path) -> None:
    server = create_server()
    _call_tool(server, "create_project", {"project_root": str(tmp_path)})
    _call_tool(
        server,
        "create_timeline",
        {"project_root": str(tmp_path), "timeline_id": "main", "name": "Main"},
    )

    with pytest.raises(ToolError, match="outside timeline bounds"):
        _call_tool(
            server,
            "add_transition",
            {
                "project_root": str(tmp_path),
                "timeline_id": "main",
                "node_id": "fade",
                "index": 1,
            },
        )


def _call_tool(server, name: str, arguments: dict):
    _content, structured = asyncio.run(server.call_tool(name, arguments))
    return structured
