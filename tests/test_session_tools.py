import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_session_tools_not_exposed_by_default() -> None:
    code = (
        "import asyncio\n"
        "from server.mcp_server import mcp\n"
        "print(sorted(t.name for t in asyncio.run(mcp.list_tools())))\n"
    )
    env = {**os.environ, "MCP_EXPOSE_SESSION_TOOLS": ""}
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "list_sessions" not in result.stdout
    assert "delete_session" not in result.stdout


def test_session_tools_exposed_when_enabled() -> None:
    code = (
        "import asyncio\n"
        "from server.mcp_server import mcp\n"
        "names = sorted(t.name for t in asyncio.run(mcp.list_tools()))\n"
        "assert 'list_sessions' in names and 'delete_session' in names, names\n"
    )
    env = {**os.environ, "MCP_EXPOSE_SESSION_TOOLS": "true"}
    result = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
