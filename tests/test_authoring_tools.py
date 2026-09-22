import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _tool_names(extra_env: dict[str, str]) -> str:
    code = (
        "import asyncio\n"
        "from server.mcp_server import mcp\n"
        "print(sorted(t.name for t in asyncio.run(mcp.list_tools())))\n"
    )
    env = {**os.environ, **extra_env}
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_validate_scenario_always_exposed() -> None:
    assert "validate_scenario" in _tool_names({"MCP_EXPOSE_AUTHORING_TOOLS": ""})


def test_authoring_mutations_not_exposed_by_default() -> None:
    names = _tool_names({"MCP_EXPOSE_AUTHORING_TOOLS": ""})
    assert "create_scenario" not in names
    assert "delete_scenario" not in names


def test_authoring_mutations_exposed_when_enabled() -> None:
    names = _tool_names({"MCP_EXPOSE_AUTHORING_TOOLS": "true"})
    assert "create_scenario" in names
    assert "delete_scenario" in names
