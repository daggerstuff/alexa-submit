"""Browser-based Alexa+ multimodal simulator page.

A single, dependency-free HTML/JS route (``GET /simulator``) served by the
same Starlette app that exposes ``/mcp``. It exists because the Alexa+ track
rules require the submission to clearly show the project working as the
end user experiences it: a voice conversation, not terminal output.

The page is a live MCP client. Every interaction on the left pane — start a
scenario, speak a practitioner turn, evaluate — is a real JSON-RPC call to the
Streamable HTTP endpoint on the same origin, and every call is surfaced in the
right pane's MCP inspector with its request, duration, and structured result.
Voice input uses the browser Web Speech API when available (Amazon Polly or
Nova Sonic can be swapped in server-side by a voice adapter consuming the
``ssml`` field), and patient replies are read aloud through
``speechSynthesis`` using the same emotion→prosody mapping the server applies
to SSML, so the browser preview and the Alexa+ read-back stay in sync.
"""

from __future__ import annotations

import json
import os

from starlette.responses import HTMLResponse, RedirectResponse, Response

from server._version import __version__
from server.voice import EMOTION_PROSODY

# Sentinel markers replaced in simulator_page(); the page ships as a plain
# constant so no templating engine or file IO is needed to serve it.
_PROSODY_TOKEN = "__EMOTION_PROSODY_JSON__"
_VERSION_TOKEN = "__APP_VERSION__"
_MCP_PATH_TOKEN = "__MCP_PATH__"

SIMULATOR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clinical Conversation Coach — Alexa+ Simulator</title>
<style>
  :root {
    --bg: #0B0F1A;
    --panel: #12151F;
    --panel-2: #1A1F2E;
    --line: rgba(255,255,255,0.07);
    --line-2: rgba(255,255,255,0.12);
    --text: #F4F6FB;
    --muted: #9AA6B8;
    --faint: #6B7686;
    --cyan: #22D3EE;
    --cyan-dim: rgba(34,211,238,0.16);
    --green: #34D399;
    --green-dim: rgba(52,211,153,0.14);
    --amber: #F59E0B;
    --red: #EF4444;
    --red-dim: rgba(239,68,68,0.14);
    --mono: ui-monospace, "SF Mono", "Cascadia Code", "JetBrains Mono", Menlo, Consolas, monospace;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", Helvetica, Arial, sans-serif;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body {
    margin: 0; background: var(--bg); color: var(--text); font-family: var(--sans);
    display: flex; flex-direction: column; min-height: 100vh;
  }
  /* ---------- top bar ---------- */
  header {
    display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
    padding: 12px 20px; background: var(--panel-2); border-bottom: 1px solid var(--line);
  }
  .brand { display: flex; align-items: baseline; gap: 10px; }
  .brand h1 { font-size: 16px; margin: 0; font-weight: 700; letter-spacing: 0.2px; }
  .brand .sub { color: var(--muted); font-size: 12.5px; }
  .spacer { flex: 1; }
  .chip {
    display: inline-flex; align-items: center; gap: 7px; padding: 5px 11px; border-radius: 999px;
    font-size: 12px; border: 1px solid var(--line-2); color: var(--muted); background: var(--panel);
    white-space: nowrap;
  }
  .chip .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--faint); }
  .chip.ok .dot { background: var(--green); box-shadow: 0 0 8px var(--green); }
  .chip.live .dot { background: var(--cyan); box-shadow: 0 0 8px var(--cyan); }
  .chip.warn .dot { background: var(--amber); box-shadow: 0 0 8px var(--amber); }
  .chip.err .dot { background: var(--red); box-shadow: 0 0 8px var(--red); }
  .disclaimer-chip { color: var(--amber); border-color: rgba(245,158,11,0.4); }
  /* ---------- layout ---------- */
  main {
    flex: 1; display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(360px, 1fr);
    gap: 16px; padding: 16px 20px; width: 100%; max-width: 1680px; margin: 0 auto;
    align-items: stretch;
  }
  @media (max-width: 980px) { main { grid-template-columns: 1fr; } }
  .pane {
    background: var(--panel); border: 1px solid var(--line); border-radius: 14px;
    display: flex; flex-direction: column; min-height: 0; overflow: hidden;
  }
  .pane-head {
    display: flex; align-items: center; gap: 10px; padding: 12px 16px;
    border-bottom: 1px solid var(--line); background: var(--panel-2);
    font-size: 12px; color: var(--muted); letter-spacing: 1.4px; text-transform: uppercase; font-weight: 700;
  }
  .pane-head .tag { color: var(--faint); font-weight: 500; letter-spacing: 0.4px; text-transform: none; }
  /* ---------- left: voice experience ---------- */
  .controls { display: flex; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--line); flex-wrap: wrap; align-items: center; }
  select, button, input[type="text"], input[type="password"] {
    font-family: var(--sans); font-size: 13.5px; color: var(--text);
    background: var(--panel-2); border: 1px solid var(--line-2); border-radius: 9px;
    padding: 8px 12px; outline: none;
  }
  select:focus-visible, button:focus-visible, input:focus-visible { border-color: var(--cyan); box-shadow: 0 0 0 2px var(--cyan-dim); }
  select { max-width: 260px; }
  button { cursor: pointer; font-weight: 600; transition: background 120ms, border-color 120ms, opacity 120ms; }
  button:hover:not(:disabled) { border-color: var(--cyan); }
  button:disabled { opacity: 0.45; cursor: not-allowed; }
  button.primary { background: linear-gradient(180deg, #1d7f92, #14667a); border-color: #2aa4bd; color: #EAFDFF; }
  button.primary:hover:not(:disabled) { background: linear-gradient(180deg, #2495ac, #17758d); }
  button.evaluate { background: linear-gradient(180deg, #8a6a17, #6d5312); border-color: #b8860b55; color: #FFF6DE; }
  button.end { background: linear-gradient(180deg, #7f1d1d, #5c1414); border-color: #b91c1c66; color: #FFECEC; }
  button.ghost { background: transparent; }
  .api-key { display: flex; align-items: center; gap: 6px; margin-left: auto; }
  .api-key input { width: 150px; padding: 7px 10px; font-size: 12px; }
  .api-key label { font-size: 11.5px; color: var(--faint); }
  .voice-stage {
    display: flex; flex-direction: column; align-items: center; gap: 10px;
    padding: 22px 16px 10px;
  }
  /* Alexa-style orb */
  .orb-wrap { position: relative; width: 118px; height: 118px; display: grid; place-items: center; }
  .orb-ring {
    position: absolute; inset: 0; border-radius: 50%;
    background: conic-gradient(from 0deg, transparent 0 68%, var(--cyan) 86%, transparent 100%);
    -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 6px));
    mask: radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 6px));
    animation: spin 9s linear infinite; opacity: 0.55;
  }
  .orb-core {
    width: 84px; height: 84px; border-radius: 50%;
    background:
      radial-gradient(circle at 34% 30%, rgba(148, 233, 255, 0.95), rgba(34, 211, 238, 0.55) 42%, rgba(8, 60, 84, 0.9) 78%),
      radial-gradient(circle at 50% 120%, #0e4c5e, #071a22 70%);
    box-shadow: 0 0 34px rgba(34,211,238,0.35), inset 0 0 22px rgba(255,255,255,0.22);
    animation: breathe 3.6s ease-in-out infinite;
    display: grid; place-items: center;
  }
  .orb-core::after {
    content: ""; width: 26px; height: 26px; border-radius: 50%;
    background: radial-gradient(circle at 40% 34%, #fff, #bdeeff 55%, transparent 75%);
    opacity: 0.9; filter: blur(1px);
  }
  .orb-wrap.listening .orb-ring { animation: spin 2.4s linear infinite; opacity: 1; }
  .orb-wrap.listening .orb-core { box-shadow: 0 0 46px rgba(52,211,153,0.55), inset 0 0 22px rgba(255,255,255,0.3); animation: breathe 1.2s ease-in-out infinite; }
  .orb-wrap.speaking .orb-ring { animation: spin 1.6s linear infinite; opacity: 1; }
  .orb-wrap.speaking .orb-core { box-shadow: 0 0 52px rgba(34,211,238,0.75), inset 0 0 26px rgba(255,255,255,0.4); animation: breathe 1s ease-in-out infinite; }
  .orb-wrap.off .orb-ring { display: none; }
  .orb-wrap.off .orb-core { background: radial-gradient(circle at 40% 34%, #3a4250, #232936 70%); box-shadow: none; animation: none; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes breathe { 0%,100% { transform: scale(1); } 50% { transform: scale(1.07); } }
  .orb-caption { font-size: 12px; color: var(--faint); letter-spacing: 0.4px; min-height: 16px; }
  .scenario-goal {
    margin: 4px 16px 10px; padding: 10px 14px; border-radius: 10px; font-size: 13px; line-height: 1.5;
    background: var(--cyan-dim); border: 1px solid rgba(34,211,238,0.25); color: #D9F6FC; display: none;
  }
  .scenario-goal.show { display: block; }
  /* transcript */
  .transcript {
    flex: 1; overflow-y: auto; padding: 12px 18px; display: flex; flex-direction: column; gap: 10px; min-height: 220px;
    scroll-behavior: smooth;
  }
  .bubble { max-width: 82%; padding: 10px 14px; border-radius: 14px; font-size: 14.5px; line-height: 1.5; animation: rise 240ms ease-out; }
  .bubble.patient { align-self: flex-start; background: #17202F; border: 1px solid var(--line); border-bottom-left-radius: 4px; }
  .bubble.learner { align-self: flex-end; background: #14251D; border: 1px solid rgba(52,211,153,0.2); border-bottom-right-radius: 4px; }
  @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
  .bubble .who { font-size: 10.5px; letter-spacing: 1.1px; text-transform: uppercase; font-weight: 700; margin-bottom: 4px; }
  .bubble.patient .who { color: var(--cyan); }
  .bubble.learner .who { color: var(--green); }
  .bubble .meta { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 7px; }
  .pill { font-size: 10.5px; letter-spacing: 0.5px; padding: 2px 8px; border-radius: 999px; text-transform: uppercase; font-weight: 700; }
  .pill.emotion { color: var(--cyan); background: var(--cyan-dim); border: 1px solid rgba(34,211,238,0.3); }
  .pill.fact { color: var(--green); background: var(--green-dim); border: 1px solid rgba(52,211,153,0.3); }
  .pill.withheld { color: var(--amber); background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.3); }
  .pill.safety { color: #FFC9C9; background: var(--red-dim); border: 1px solid rgba(239,68,68,0.45); }
  .safety-banner {
    margin: 0 18px 10px; padding: 10px 14px; border-radius: 10px; font-size: 13.5px; line-height: 1.5;
    background: var(--red-dim); border: 1px solid rgba(239,68,68,0.45); color: #FFD9D9; display: none;
  }
  .safety-banner.show { display: block; }
  /* input row */
  .input-row { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--line); align-items: center; }
  .mic {
    width: 44px; height: 44px; border-radius: 50%; flex: none; display: grid; place-items: center;
    background: var(--panel-2); border: 1px solid var(--line-2); font-size: 17px; padding: 0;
  }
  .mic.rec { background: #0d3d31; border-color: var(--green); box-shadow: 0 0 14px rgba(52,211,153,0.4); }
  .input-row input[type="text"] { flex: 1; }
  .suggestions { display: flex; gap: 6px; flex-wrap: wrap; padding: 0 16px 10px; }
  .suggestion {
    font-size: 12px; color: var(--muted); background: transparent; border: 1px dashed var(--line-2);
    border-radius: 999px; padding: 5px 11px; cursor: pointer; font-weight: 500;
  }
  .suggestion:hover { color: var(--cyan); border-color: var(--cyan); }
  .tts-row { display: flex; align-items: center; gap: 8px; padding: 0 16px 12px; font-size: 12px; color: var(--faint); }
  .tts-row label { display: flex; gap: 6px; align-items: center; cursor: pointer; }
  /* ---------- right: MCP inspector ---------- */
  .inspector { font-family: var(--mono); }
  .meter-block { padding: 14px 16px 10px; border-bottom: 1px solid var(--line); }
  .meter-label { display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
  .meter-label b { color: var(--text); font-size: 13px; }
  .meter { position: relative; height: 10px; border-radius: 6px; background: linear-gradient(90deg, #7f1d1d, #3a4250 38%, #3a4250 62%, #14532d); opacity: 0.92; }
  .meter .tick { position: absolute; top: -3px; width: 1px; height: 16px; background: rgba(255,255,255,0.25); }
  .meter .needle {
    position: absolute; top: -5px; width: 4px; height: 20px; border-radius: 2px; background: #fff;
    box-shadow: 0 0 8px rgba(255,255,255,0.6); transition: left 400ms cubic-bezier(.3,.7,.3,1); left: 50%;
  }
  .facts-block { padding: 12px 16px; border-bottom: 1px solid var(--line); }
  .block-title { font-size: 11px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; font-weight: 700; }
  .fact-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .fact-chip {
    font-size: 11.5px; padding: 3px 9px; border-radius: 6px; color: var(--faint);
    border: 1px solid var(--line); background: var(--panel-2);
  }
  .fact-chip.lit { color: #B9F5DE; background: var(--green-dim); border-color: rgba(52,211,153,0.4); animation: pop 300ms ease-out; }
  @keyframes pop { 0% { transform: scale(1.25); } 100% { transform: scale(1); } }
  .rubric-block { padding: 12px 16px; border-bottom: 1px solid var(--line); display: none; }
  .rubric-block.show { display: block; }
  .rubric-row { display: flex; align-items: center; gap: 9px; padding: 5px 0; font-size: 12px; }
  .rubric-check {
    width: 15px; height: 15px; border-radius: 4px; border: 1.5px solid var(--line-2); flex: none;
    display: grid; place-items: center; font-size: 10px; color: #0B0F1A;
  }
  .rubric-row.lit .rubric-check { background: var(--green); border-color: var(--green); }
  .rubric-row.lit .rubric-check::after { content: "✓"; font-weight: 900; }
  .rubric-name { flex: 1; color: var(--text); }
  .rubric-row .score { color: var(--cyan); font-weight: 700; }
  .rubric-bar { position: relative; flex: 1.1; height: 6px; border-radius: 4px; background: var(--panel-2); overflow: hidden; }
  .rubric-bar i { position: absolute; inset: 0; background: linear-gradient(90deg, #0e7490, var(--cyan)); transform: scaleX(0); transform-origin: left; transition: transform 500ms ease; }
  .log-block { flex: 1; overflow-y: auto; padding: 10px 14px; display: flex; flex-direction: column; gap: 7px; min-height: 200px; }
  .log-entry { font-size: 11.5px; line-height: 1.55; padding: 5px 10px; background: var(--panel-2); border-radius: 7px; animation: rise 200ms ease-out; }
  .log-entry .l1 { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
  .log-entry .mark { color: var(--green); font-weight: 700; }
  .log-entry .method { color: var(--cyan); font-weight: 700; }
  .log-entry .tool { color: #A5F3FC; }
  .log-entry .ms { color: var(--faint); margin-left: auto; }
  .log-entry .args { color: var(--muted); word-break: break-all; }
  .log-entry.ok .mark { color: var(--green); }
  .log-entry.err .mark { color: var(--red); }
  .log-entry.err .method { color: #FFB4B4; }
  .log-entry .detail { color: var(--muted); }
  .empty-note { color: var(--faint); font-size: 12px; padding: 8px 2px; }
  footer {
    padding: 10px 20px; border-top: 1px solid var(--line); color: var(--faint); font-size: 11.5px;
    display: flex; gap: 14px; flex-wrap: wrap; background: var(--panel-2);
  }
  footer span b { color: var(--muted); font-weight: 600; }
  @media (prefers-reduced-motion: reduce) {
    .orb-ring, .orb-core, .bubble, .fact-chip, .log-entry { animation: none !important; }
  }
</style>
</head>
<body>
<header>
  <div class="brand">
    <h1>Clinical Conversation Coach</h1>
    <span class="sub">Alexa+ multimodal simulator</span>
  </div>
  <div class="spacer"></div>
  <span class="chip" id="statusChip"><span class="dot"></span><span id="statusText">connecting…</span></span>
  <span class="chip disclaimer-chip" title="This simulator is for educational practice only.">educational simulation only</span>
</header>

<main>
  <!-- ============ left pane: the Alexa+ voice experience ============ -->
  <section class="pane" aria-label="Alexa+ voice experience">
    <div class="pane-head">Alexa+ voice experience <span class="tag">speak as the practitioner</span></div>
    <div class="controls">
      <select id="scenarioSelect" title="Scenario" disabled><option>loading scenarios…</option></select>
      <button id="startBtn" class="primary" disabled>Start</button>
      <button id="evaluateBtn" class="evaluate" disabled>Evaluate</button>
      <button id="endBtn" class="end" disabled>End</button>
      <div class="api-key">
        <label for="apiKey">API key</label>
        <input type="password" id="apiKey" placeholder="optional" autocomplete="off" title="Sent as Authorization: Bearer + X-API-Key when the endpoint requires one">
      </div>
    </div>
    <div class="voice-stage">
      <div class="orb-wrap off" id="orb"><div class="orb-ring"></div><div class="orb-core"></div></div>
      <div class="orb-caption" id="orbCaption">start a scenario to begin</div>
    </div>
    <div class="scenario-goal" id="scenarioGoal"></div>
    <div class="transcript" id="transcript" aria-live="polite"></div>
    <div class="safety-banner" id="safetyBanner"></div>
    <div class="suggestions" id="suggestions"></div>
    <div class="input-row">
      <button class="mic" id="micBtn" title="Speak as the practitioner (Web Speech API)" aria-label="Speak practitioner turn">🎙</button>
      <input type="text" id="turnInput" placeholder="Ask the patient a question…" disabled
             aria-label="Practitioner turn" autocomplete="off">
      <button id="sendBtn" class="primary" disabled>Send</button>
    </div>
    <div class="tts-row">
      <label><input type="checkbox" id="ttsToggle" checked> read patient replies aloud (prosody-matched TTS)</label>
      <span id="voiceHint" style="margin-left:auto"></span>
    </div>
  </section>

  <!-- ============ right pane: the MCP inspector ============ -->
  <section class="pane inspector" aria-label="MCP inspector">
    <div class="pane-head">MCP inspector <span class="tag" id="endpointTag"></span></div>
    <div class="meter-block">
      <div class="meter-label"><span>patient rapport / trust</span><b id="rapportValue">0</b></div>
      <div class="meter" id="rapportMeter">
        <span class="tick" style="left:0%"></span>
        <span class="tick" style="left:25%"></span>
        <span class="tick" style="left:50%"></span>
        <span class="tick" style="left:75%"></span>
        <span class="tick" style="left:100%"></span>
        <span class="needle" id="rapportNeedle"></span>
      </div>
    </div>
    <div class="facts-block">
      <div class="block-title">disclosed facts <span id="withheldNote" style="color:var(--amber)"></span></div>
      <div class="fact-chips" id="factChips"><span class="empty-note">facts appear as the patient discloses them</span></div>
    </div>
    <div class="rubric-block" id="rubricBlock">
      <div class="block-title">clinical rubric <span id="rubricScore" style="color:var(--cyan)"></span></div>
      <div id="rubricRows"></div>
      <div class="detail" id="rubricSummary" style="color:var(--muted); font-size:12px; margin-top:6px;"></div>
    </div>
    <div class="log-block" id="logBlock" aria-live="polite">
      <div class="empty-note" id="logEmpty">JSON-RPC calls over Streamable HTTP appear here…</div>
    </div>
  </section>
</main>

<footer>
  <span><b>MCP</b> <span id="footerProto">2025-11-25</span> · Streamable HTTP</span>
  <span><b>session</b> <span id="footerSession">—</span></span>
  <span><b>server</b> clinical-conversation-coach <span id="footerVersion"></span></span>
  <span>educational simulation only — never use for real patient care</span>
</footer>

<script>
(function () {
  "use strict";
  var MCP_PATH = "__MCP_PATH__";
  var PROSODY = __EMOTION_PROSODY_JSON__;
  var reqId = 0;
  var sessionId = null;            // MCP transport session id (Mcp-Session-Id header)
  var appSessionId = null;         // application-level simulation session id
  var scenarios = [];
  var simActive = false;
  var $ = function (id) { return document.getElementById(id); };

  /* ---------------- inspector log ---------------- */
  function log(method, tool, argsText, ok, ms, detail) {
    var empty = $("logEmpty"); if (empty) empty.remove();
    var row = document.createElement("div");
    row.className = "log-entry " + (ok === false ? "err" : "ok");
    var l1 = document.createElement("div"); l1.className = "l1";
    var mark = document.createElement("span"); mark.className = "mark"; mark.textContent = "▸";
    l1.appendChild(mark);
    var m = document.createElement("span"); m.className = "method"; m.textContent = method;
    l1.appendChild(m);
    if (tool) { var t = document.createElement("span"); t.className = "tool"; t.textContent = tool; l1.appendChild(t); }
    var msEl = document.createElement("span"); msEl.className = "ms"; msEl.textContent = ms + " ms";
    l1.appendChild(msEl);
    row.appendChild(l1);
    if (argsText) { var a = document.createElement("div"); a.className = "args"; a.textContent = argsText; row.appendChild(a); }
    if (detail) { var d = document.createElement("div"); d.className = "detail"; d.textContent = detail; row.appendChild(d); }
    $("logBlock").appendChild(row);
    $("logBlock").scrollTop = $("logBlock").scrollHeight;
  }

  /* ---------------- status ---------------- */
  function setStatus(text, cls) {
    $("statusText").textContent = text;
    $("statusChip").className = "chip " + (cls || "");
  }
  function setOrb(state, caption) {
    $("orb").className = "orb-wrap " + state;
    if (caption !== undefined) $("orbCaption").textContent = caption;
  }

  /* ---------------- MCP client ---------------- */
  function headers(extra) {
    var h = {
      "content-type": "application/json",
      "accept": "application/json, text/event-stream"
    };
    if (sessionId) h["mcp-session-id"] = sessionId;
    var key = $("apiKey").value.trim();
    if (key) { h["authorization"] = "Bearer " + key; h["x-api-key"] = key; }
    return Object.assign(h, extra || {});
  }

  function post(body, opts) {
    return fetch(MCP_PATH, { method: "POST", headers: headers(), body: JSON.stringify(body) })
      .then(function (res) {
        if (res.status === 404 && sessionId && !(opts && opts.isRetry)) {
          // The Streamable HTTP session expired (idle timeout). Re-initialize
          // once and retry; the clinical session itself survives server-side.
          sessionId = null;
          return initializeRaw().then(function () { return post(body, { isRetry: true }); });
        }
        if (res.status === 401 || res.status === 403) {
          setStatus("unauthorized — enter the API key", "err");
          throw new Error("The endpoint requires an API key (enter it top-left).");
        }
        if (res.status === 429) {
          setStatus("rate limited — wait a moment", "warn");
          throw new Error("Rate limit exceeded; wait a moment and try again.");
        }
        return res.json().then(function (json) {
          if (!res.ok) throw new Error(json.error ? json.error.message : "HTTP " + res.status);
          return json;
        });
      });
  }

  // Initialize needs the raw response to read the Mcp-Session-Id header.
  function initializeRaw() {
    var t0 = performance.now();
    return fetch(MCP_PATH, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ jsonrpc: "2.0", id: ++reqId, method: "initialize", params: {
        protocolVersion: "2025-11-25",
        capabilities: {},
        clientInfo: { name: "browser-simulator", version: "1.0.0" }
      }})
    }).then(function (res) {
      if (res.status === 401 || res.status === 403) {
        setStatus("unauthorized — enter the API key", "err");
        throw new Error("The endpoint requires an API key (enter it top-left).");
      }
      if (res.status === 429) {
        setStatus("rate limited — wait a moment", "warn");
        throw new Error("Rate limit exceeded; wait a moment and try again.");
      }
      return res.json().then(function (json) {
        var ms = Math.round(performance.now() - t0);
        sessionId = res.headers.get("mcp-session-id") || sessionId;
        var pv = json && json.result ? json.result.protocolVersion : "?";
        log("initialize", null, "protocolVersion " + pv + " · client browser-simulator", res.ok, ms,
            "server: " + (json && json.result && json.result.serverInfo ? json.result.serverInfo.name + " " + json.result.serverInfo.version : ""));
        $("footerProto").textContent = pv;
        $("footerSession").textContent = sessionId ? sessionId.slice(0, 8) + "…" : "—";
        return post({ jsonrpc: "2.0", method: "notifications/initialized" });
      });
    });
  }

  function callTool(name, args) {
    var t0 = performance.now();
    var argsText = name + "(" + Object.keys(args).map(function (k) {
      var v = String(args[k]);
      return k + "=" + (v.length > 42 ? v.slice(0, 42) + "…" : v);
    }).join(", ") + ")";
    return post({ jsonrpc: "2.0", id: ++reqId, method: "tools/call",
                  params: { name: name, arguments: args } })
      .then(function (json) {
        var ms = Math.round(performance.now() - t0);
        if (json.error) {
          log("tools/call", name, argsText, false, ms, "error: " + json.error.message);
          throw new Error(json.error.message);
        }
        log("tools/call", name, argsText, true, ms);
        return json.result.structuredContent;
      });
  }

  function toolNames() {
    var t0 = performance.now();
    return post({ jsonrpc: "2.0", id: ++reqId, method: "tools/list", params: {} }).then(function (json) {
      var ms = Math.round(performance.now() - t0);
      var names = json.result.tools.map(function (t) { return t.name; });
      log("tools/list", null, names.length + " tools: " + names.join(" · "), true, ms);
      return names;
    });
  }

  /* ---------------- rendering ---------------- */
  function addBubble(kind, text, metaPills) {
    var b = document.createElement("div");
    b.className = "bubble " + kind;
    var who = document.createElement("div");
    who.className = "who";
    who.textContent = kind === "patient" ? "patient" : "you";
    b.appendChild(who);
    var body = document.createElement("div");
    body.textContent = text;
    b.appendChild(body);
    if (metaPills && metaPills.length) {
      var meta = document.createElement("div"); meta.className = "meta";
      metaPills.forEach(function (p) {
        var s = document.createElement("span");
        s.className = "pill " + p.cls; s.textContent = p.text;
        meta.appendChild(s);
      });
      b.appendChild(meta);
    }
    var tr = $("transcript");
    tr.appendChild(b);
    tr.scrollTop = tr.scrollHeight;
  }

  function setRapport(v) {
    v = Math.max(-3, Math.min(3, v || 0));
    $("rapportValue").textContent = (v > 0 ? "+" : "") + v;
    $("rapportNeedle").style.left = ((v + 3) / 6 * 100) + "%";
  }

  var factSet = {};
  function renderFacts(disclosed, withheld) {
    var chips = $("factChips");
    disclosed.forEach(function (f) {
      if (!factSet[f]) { factSet[f] = true; chips.appendChild(chip(f, true)); }
    });
    (withheld || []).forEach(function (f) {
      if (!factSet[f]) { factSet[f] = true; chips.appendChild(chip(f, false)); }
    });
    if (Object.keys(factSet).length) {
      var first = chips.querySelector(".empty-note"); if (first) first.remove();
    }
  }
  function chip(text, lit) {
    var s = document.createElement("span");
    s.className = "fact-chip" + (lit ? " lit" : "");
    s.textContent = text;
    return s;
  }

  function showSafety(note) {
    if (!note) return;
    var banner = $("safetyBanner");
    banner.textContent = "⚠ " + note;
    banner.classList.add("show");
  }

  function renderRubric(evaluation) {
    $("rubricBlock").classList.add("show");
    var rows = $("rubricRows"); rows.innerHTML = "";
    evaluation.metrics.forEach(function (m) {
      var row = document.createElement("div");
      row.className = "rubric-row" + (m.matched_terms && m.matched_terms.length ? " lit" : "");
      var check = document.createElement("span"); check.className = "rubric-check";
      var name = document.createElement("span"); name.className = "rubric-name";
      name.textContent = m.metric + (m.matched_terms && m.matched_terms.length ? " · " + m.matched_terms.join(", ") : "");
      var bar = document.createElement("span"); bar.className = "rubric-bar";
      var fill = document.createElement("i");
      fill.style.transform = "scaleX(0)";
      requestAnimationFrame(function () { fill.style.transform = "scaleX(" + (m.score / m.max_score) + ")"; });
      bar.appendChild(fill);
      var score = document.createElement("span"); score.className = "score";
      score.textContent = m.score + "/" + m.max_score;
      row.appendChild(check); row.appendChild(name); row.appendChild(bar); row.appendChild(score);
      rows.appendChild(row);
    });
    $("rubricScore").textContent = "· " + evaluation.overall_score + " / " + evaluation.max_score + " (rubric v" + evaluation.rubric_version + ")";
    $("rubricSummary").textContent = evaluation.summary || "";
    if (evaluation.safety_flags && evaluation.safety_flags.length) {
      showSafety("Safety flags: " + evaluation.safety_flags.join(", "));
    }
  }

  /* ---------------- voice: TTS with the server's prosody mapping ---------------- */
  function prosodyToSpeech(emotion) {
    var attrs = PROSODY[(emotion || "").toLowerCase()] || 'rate="medium" pitch="medium"';
    var rate = 1.0, pitch = 1.0, volume = 1.0;
    if (attrs.indexOf("fast") !== -1) rate = 1.18; else if (attrs.indexOf("slow") !== -1) rate = 0.84;
    if (attrs.indexOf("high") !== -1) pitch = 1.35; else if (attrs.indexOf("low") !== -1) pitch = 0.75;
    if (attrs.indexOf("soft") !== -1) volume = 0.72;
    return { rate: rate, pitch: pitch, volume: volume };
  }

  function speak(text, emotion) {
    if (!$("ttsToggle").checked || !("speechSynthesis" in window) || !text) return;
    try {
      var u = new SpeechSynthesisUtterance(text);
      var p = prosodyToSpeech(emotion);
      u.rate = p.rate; u.pitch = p.pitch; u.volume = p.volume;
      var voices = window.speechSynthesis.getVoices();
      for (var i = 0; i < voices.length; i++) {
        if (/en[-_](US|GB)/i.test(voices[i].lang)) { u.voice = voices[i]; break; }
      }
      u.onstart = function () { setOrb("speaking"); };
      u.onend = function () {
        setOrb("idle", simActive ? "listening for your turn" : "session idle");
      };
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
      setOrb("speaking");
    } catch (e) { /* TTS is best-effort; the transcript is the source of truth */ }
  }

  /* ---------------- voice: Web Speech API input ---------------- */
  var recog = null, recognizing = false;
  function setupRecognition() {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      $("micBtn").disabled = true;
      $("micBtn").title = "Voice input is not supported in this browser — type your turns instead";
      $("voiceHint").textContent = "voice input unavailable in this browser";
      return;
    }
    recog = new SR();
    recog.lang = "en-US";
    recog.interimResults = true;
    recog.maxAlternatives = 1;
    recog.onstart = function () {
      recognizing = true;
      $("micBtn").classList.add("rec");
      setOrb("listening", "listening…");
    };
    recog.onresult = function (event) {
      var text = "";
      for (var i = event.resultIndex; i < event.results.length; i++) {
        text += event.results[i][0].transcript;
      }
      $("turnInput").value = text;
    };
    recog.onerror = function (event) {
      setOrb("idle", "voice input error — type instead");
      if (event.error === "not-allowed") $("voiceHint").textContent = "microphone permission denied";
    };
    recog.onend = function () {
      recognizing = false;
      $("micBtn").classList.remove("rec");
      setOrb("idle", simActive ? "listening for your turn" : "session idle");
      var said = $("turnInput").value.trim();
      if (said) sendTurn();
    };
  }
  $("micBtn").addEventListener("click", function () {
    if (!recog) return;
    if (recognizing) { recog.stop(); return; }
    try { recog.start(); } catch (e) { /* already started */ }
  });

  /* ---------------- flows ---------------- */
  function uuid() {
    return (crypto.randomUUID) ? crypto.randomUUID()
      : "xxxx".replace(/x/g, function () { return Math.floor(Math.random() * 16).toString(16); }) + Date.now();
  }

  function sendTurn() {
    var input = $("turnInput");
    var text = input.value.trim();
    if (!text || !simActive) return;
    input.value = "";
    addBubble("learner", text);
    callTool("send_practitioner_turn", {
      session_id: appSessionId,
      practitioner_message: text,
      client_event_id: uuid()
    }).then(renderPatient).catch(showError);
  }

  function renderPatient(result) {
    var patient = result.patient;
    if (!patient) return;
    var pills = [{ cls: "emotion", text: patient.emotional_state }];
    (patient.disclosed_facts || []).forEach(function (f) { pills.push({ cls: "fact", text: f }); });
    (patient.withheld_facts || []).forEach(function (f) { pills.push({ cls: "withheld", text: f + " (withheld)" }); });
    if (patient.safety_note) pills.push({ cls: "safety", text: "safety note" });
    addBubble("patient", patient.content, pills);
    setRapport(patient.rapport);
    renderFacts(patient.disclosed_facts || [], patient.withheld_facts || []);
    if (patient.safety_note) showSafety(patient.safety_note);
    speak(patient.content, patient.emotional_state);
  }

  function showError(err) {
    setStatus("error — see inspector", "err");
    addBubble("patient", "⚠ " + (err && err.message ? err.message : "The call failed."), [{ cls: "safety", text: "error" }]);
  }

  function suggestions() {
    var list = [
      "Hello, my name is Dr. Chen. Where does it hurt?",
      "Are you short of breath?",
      "What medications do you take?",
      "When did it start?"
    ];
    var box = $("suggestions"); box.innerHTML = "";
    list.forEach(function (s) {
      var b = document.createElement("button");
      b.className = "suggestion"; b.type = "button"; b.textContent = s;
      b.addEventListener("click", function () { $("turnInput").value = s; $("turnInput").focus(); });
      box.appendChild(b);
    });
  }

  /* ---------------- boot ---------------- */
  function boot() {
    $("footerVersion").textContent = "v" + "__APP_VERSION__";
    $("endpointTag").textContent = "POST " + MCP_PATH + " · session 2025-11-25";
    var savedKey = localStorage.getItem("cc-api-key");
    if (savedKey) $("apiKey").value = savedKey;
    $("apiKey").addEventListener("change", function () { localStorage.setItem("cc-api-key", $("apiKey").value.trim()); });
    suggestions();
    setupRecognition();
    if ("speechSynthesis" in window) { window.speechSynthesis.getVoices(); }
    initializeRaw().then(function () {
      return toolNames().then(function () {
        return callTool("list_simulation_scenarios", {});
      });
    }).then(function (result) {
      scenarios = result.scenarios;
      var sel = $("scenarioSelect");
      sel.innerHTML = "";
      scenarios.forEach(function (s) {
        var o = document.createElement("option");
        o.value = s.scenario_id;
        o.textContent = s.title + " (" + s.difficulty + ")";
        sel.appendChild(o);
      });
      sel.disabled = false;
      $("startBtn").disabled = false;
      setStatus("connected — pick a scenario and press Start", "ok");
      setOrb("off", "start a scenario to begin");
    }).catch(function (err) {
      setStatus("cannot reach the MCP endpoint", "err");
      log("error", null, String(err && err.message ? err.message : err), false, 0);
    });

    $("startBtn").addEventListener("click", function () {
      if (simActive) return;
      appSessionId = "sim-" + uuid().slice(0, 8);
      $("transcript").innerHTML = "";
      $("safetyBanner").classList.remove("show");
      $("rubricBlock").classList.remove("show");
      factSet = {}; $("factChips").innerHTML = '<span class="empty-note">facts appear as the patient discloses them</span>';
      callTool("start_simulation", { session_id: appSessionId, scenario_id: $("scenarioSelect").value })
        .then(function (result) {
          simActive = true;
          $("startBtn").disabled = true;
          $("evaluateBtn").disabled = false;
          $("endBtn").disabled = false;
          $("turnInput").disabled = false;
          $("sendBtn").disabled = false;
          setStatus("active · " + result.scenario_id + " v" + result.scenario_version, "live");
          if (result.goal) {
            $("scenarioGoal").textContent = "Goal: " + result.goal;
            $("scenarioGoal").classList.add("show");
          }
          renderPatient(result);
        }).catch(showError);
    });

    $("sendBtn").addEventListener("click", sendTurn);
    $("turnInput").addEventListener("keydown", function (e) {
      if (e.key === "Enter") sendTurn();
    });

    $("evaluateBtn").addEventListener("click", function () {
      callTool("evaluate_simulation", { session_id: appSessionId }).then(function (result) {
        renderRubric(result.evaluation);
        setRapport(result.evaluation.rapport_score);
        setStatus("evaluated · " + result.evaluation.overall_score + "/" + result.evaluation.max_score, "ok");
        speak(result.evaluation.spoken_summary || result.evaluation.summary, "calm");
      }).catch(showError);
    });

    $("endBtn").addEventListener("click", function () {
      callTool("end_simulation", { session_id: appSessionId }).then(function (result) {
        simActive = false;
        if (result.evaluation) renderRubric(result.evaluation);
        $("startBtn").disabled = false;
        $("evaluateBtn").disabled = true;
        $("endBtn").disabled = true;
        $("turnInput").disabled = true;
        $("sendBtn").disabled = true;
        setStatus("ended — press Start for a new session", "ok");
        setOrb("off", "session ended — start again anytime");
      }).catch(showError);
    });
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
</script>
</body>
</html>
"""

_page_cache: dict[str, str] = {}


def simulator_page(mcp_path: str | None = None) -> HTMLResponse:
    """Render the simulator page with live tokens injected.

    The emotion→prosody table is embedded from ``server.voice`` at serve time,
    so the browser preview and the server's SSML can never drift apart.
    """
    path = mcp_path or os.getenv("MCP_PATH", "/mcp")
    key = f"{path}:{__version__}"
    if key not in _page_cache:
        _page_cache[key] = (
            SIMULATOR_HTML.replace(_MCP_PATH_TOKEN, path)
            .replace(_PROSODY_TOKEN, json.dumps(EMOTION_PROSODY))
            .replace(_VERSION_TOKEN, __version__)
        )
    return HTMLResponse(_page_cache[key])


def simulator_response(path: str, mcp_path: str | None = None) -> Response | None:
    """Return the public browser routes, or None to fall through to /mcp.

    ``GET /simulator`` serves the page unauthenticated (it contains no data;
    every MCP call it makes still passes the endpoint's auth middleware), and
    ``GET /`` redirects to it so a judge hitting the service root lands on
    the experience rather than a 404.
    """
    if path == "/simulator":
        return simulator_page(mcp_path)
    if path == "/":
        return RedirectResponse(url="/simulator", status_code=307)
    return None
