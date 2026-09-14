from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

# Make the repo root importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.mcp_server import mcp  # noqa: E402


def _type_str(schema: dict[str, Any]) -> str:
    if "anyOf" in schema:
        return " | ".join(str(item.get("type", "null")) for item in schema["anyOf"])
    return str(schema.get("type", "object"))


def _constraints(prop: dict[str, Any]) -> str:
    limits = []
    if prop.get("maxLength") is not None:
        limits.append(f"maxLength={prop['maxLength']}")
    if prop.get("minLength") is not None:
        limits.append(f"minLength={prop['minLength']}")
    return ", ".join(limits)


async def _render() -> str:
    tools = await mcp.list_tools()
    lines: list[str] = [
        "# MCP tool reference",
        "",
        "Generated from the MCP server tool schemas by `scripts/gen_tool_reference.py`.",
        "Do not edit by hand; regenerate after changing a tool signature.",
        "",
    ]
    for tool in tools:
        schema: dict[str, Any] = tool.input_schema or {}
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        lines.append(f"## `{tool.name}`")
        lines.append("")
        lines.append(tool.description)
        lines.append("")
        if properties:
            lines.append("| Parameter | Type | Required | Default | Description |")
            lines.append("| --- | --- | --- | --- | --- |")
            for name, prop in properties.items():
                typ = _type_str(prop)
                constraints = _constraints(prop)
                if constraints:
                    typ += f" ({constraints})"
                req = "yes" if name in required else "no"
                default = prop.get("default")
                default_str = "—" if default is None else f"`{default}`"
                lines.append(f"| `{name}` | {typ} | {req} | {default_str} | {prop.get('description', '')} |")
        else:
            lines.append("No input parameters.")
        lines.append("")
        out = tool.output_schema or {}
        title = out.get("title", out.get("type", "object"))
        lines.append(f"Output: structured `{title}`.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    print(asyncio.run(_render()), end="")
