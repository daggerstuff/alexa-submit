"""Tests for the browser-based Alexa+ simulator page.

The page is a live MCP client rendered by the same Starlette app that serves
/mcp, so these tests assert what a judge's browser depends on: the route is
served, the page's JavaScript drives the real tool surface, and the emotion
→ prosody mapping embedded in the page can never drift from the one the
server applies to SSML.
"""

from __future__ import annotations

import json
import re

from starlette.testclient import TestClient

from server.mcp_server import create_app
from server.voice import EMOTION_PROSODY

CORE_TOOLS = (
    "list_simulation_scenarios",
    "start_simulation",
    "send_practitioner_turn",
    "evaluate_simulation",
    "end_simulation",
)


def _client() -> TestClient:
    return TestClient(create_app())


def test_simulator_page_is_served() -> None:
    with _client() as client:
        response = client.get("/simulator")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        page = response.text
        assert "Clinical Conversation Coach" in page
        assert "MCP inspector" in page
        assert "Alexa+ voice experience" in page
        assert "educational simulation only" in page.lower()


def test_root_redirects_to_simulator() -> None:
    with _client() as client:
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/simulator"
        followed = client.get("/", follow_redirects=True)
        assert followed.status_code == 200
        assert "Clinical Conversation Coach" in followed.text


def test_simulator_drives_the_real_tool_surface() -> None:
    with _client() as client:
        page = client.get("/simulator").text
        # Every core tool the page can invoke must be present in its JS.
        for tool in CORE_TOOLS:
            assert tool in page, f"simulator page lost the {tool} tool call"
        # It negotiates the required protocol revision, not a placeholder.
        assert '"2025-11-25"' in page
        # Voice input and read-aloud are wired through the browser speech APIs.
        assert "SpeechRecognition" in page or "webkitSpeechRecognition" in page
        assert "speechSynthesis" in page
        # Retries survive an expired Streamable HTTP session (404 → re-init).
        assert "res.status === 404" in page


def test_simulator_embeds_the_server_prosody_map() -> None:
    """The page's TTS prosody must match server.voice exactly.

    The emotion→prosody table is injected from ``EMOTION_PROSODY`` at serve
    time; this pins the invariant so a new scenario emotion cannot silently
    read in the neutral voice in the browser while sounding expressive via
    SSML on Alexa.
    """
    with _client() as client:
        page = client.get("/simulator").text
    match = re.search(r"var PROSODY = (\{.*?\});\n", page, re.DOTALL)
    assert match is not None, "prosody map not embedded in the simulator page"
    embedded = json.loads(match.group(1))
    assert embedded == {key: value for key, value in EMOTION_PROSODY.items()}


def test_simulator_page_mentions_app_version() -> None:
    from server._version import __version__

    with _client() as client:
        page = client.get("/simulator").text
    assert __version__ in page
