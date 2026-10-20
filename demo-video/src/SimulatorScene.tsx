import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * SimulatorScene — the Alexa+ multimodal experience, synthesized.
 *
 * Renders the browser simulator page (GET /simulator served by the MCP app)
 * as a deterministic Remotion scene: a split screen where the left pane is the
 * voice experience (orb, live transcript, spoken takeaway) and the right pane
 * is the MCP inspector (JSON-RPC calls, rapport meter, disclosed facts, rubric
 * checkboxes). The two panes animate from one event timeline so every spoken
 * turn visibly drives a real tool call.
 *
 * Step kinds (all times in scene seconds):
 *   { at, kind: "log",      method, tool?, args, ms? }  — inspector JSON-RPC row
 *   { at, kind: "learner",  text }                       — practitioner bubble
 *   { at, kind: "patient",  text, emotion }              — patient bubble + TTS
 *   { at, kind: "fact",     id }                         — disclosed-fact chip pops
 *   { at, kind: "rapport",  value }                      — meter needle moves
 *   { at, kind: "ui",       select | pressed | rubric | takeaway }
 *   { at, kind: "pill",     text, color?, dur? }         — floating badge
 */

type LogEvent = { at: number; kind: "log"; method: string; tool?: string; args: string; ms?: number };
type LearnerEvent = { at: number; kind: "learner"; text: string };
type PatientEvent = { at: number; kind: "patient"; text: string; emotion: string };
type FactEvent = { at: number; kind: "fact"; id: string };
type RapportEvent = { at: number; kind: "rapport"; value: number };
type UiEvent = { at: number; kind: "ui"; select?: string; pressed?: boolean; rubric?: RubricData; takeaway?: string };
type PillEvent = { at: number; kind: "pill"; text: string; color?: string; dur?: number };

type RubricRow = { name: string; matched: string[]; score: number; max: number };
type RubricData = { rows: RubricRow[]; score: string };

type SimEvent = LogEvent | LearnerEvent | PatientEvent | FactEvent | RapportEvent | UiEvent | PillEvent;

export const simulatorEvents: SimEvent[] = [
  // 0–2s: the page registers before anything moves
  { at: 2.0, kind: "log", method: "initialize", args: "protocolVersion 2025-11-25 · client browser-simulator" },
  { at: 2.7, kind: "log", method: "tools/list", args: "6 tools discovered", ms: 14 },
  { at: 3.5, kind: "ui", select: "chest-pain-basic — basic · v1.2.0" },
  { at: 5.0, kind: "ui", pressed: true },
  { at: 5.4, kind: "log", method: "tools/call", tool: "start_simulation", args: "scenario_id=chest-pain-basic", ms: 34 },
  { at: 6.4, kind: "patient", text: "Hello. I have been having pressure in my chest and I am worried.", emotion: "anxious" },
  { at: 10.0, kind: "learner", text: "Hi, my name is Dr. Chen. Where is the pain, and are you short of breath?" },
  { at: 11.0, kind: "log", method: "tools/call", tool: "send_practitioner_turn", args: "client_event_id=…4f2a", ms: 41 },
  { at: 12.2, kind: "patient", text: "It feels like pressure right in the middle of my chest. I am a little short of breath.", emotion: "concerned" },
  { at: 13.2, kind: "fact", id: "chest-pressure" },
  { at: 13.5, kind: "fact", id: "dyspnea" },
  { at: 14.4, kind: "learner", text: "I'm sorry — that sounds frightening. When did it start?" },
  { at: 15.4, kind: "log", method: "tools/call", tool: "send_practitioner_turn", args: "client_event_id=…81bc", ms: 38 },
  { at: 16.4, kind: "patient", text: "About thirty minutes ago, climbing the stairs.", emotion: "worried" },
  { at: 17.4, kind: "fact", id: "onset-activity" },
  { at: 17.7, kind: "rapport", value: 1 },
  { at: 18.6, kind: "learner", text: "Does anything make it better or worse? Any nausea or sweating?" },
  { at: 19.6, kind: "log", method: "tools/call", tool: "send_practitioner_turn", args: "client_event_id=…c7d9", ms: 37 },
  { at: 20.6, kind: "patient", text: "No nausea. The pressure is steady — nothing makes it better.", emotion: "anxious" },
  { at: 21.4, kind: "fact", id: "onset-constant" },
  { at: 22.6, kind: "learner", text: "Given your history, I want an ECG right now — is it okay if my team takes over?" },
  { at: 23.6, kind: "log", method: "tools/call", tool: "send_practitioner_turn", args: "client_event_id=…e0aa", ms: 40 },
  { at: 24.6, kind: "patient", text: "Yes — please. That is what I was hoping you would say.", emotion: "reassured" },
  { at: 25.0, kind: "rapport", value: 2 },
  { at: 26.0, kind: "log", method: "tools/call", tool: "evaluate_simulation", args: "rubric v1.2.0", ms: 52 },
  {
    at: 27.0,
    kind: "ui",
    rubric: {
      score: "13 / 20",
      rows: [
        { name: "Introduction and consent", matched: ["name", "okay"], score: 2, max: 4 },
        { name: "Symptom characterization", matched: ["where", "when", "better/worse"], score: 4, max: 4 },
        { name: "Associated symptoms and risk", matched: ["breath"], score: 2, max: 4 },
        { name: "Safety escalation", matched: ["ecg"], score: 3, max: 4 },
        { name: "Shared next-step confirmation", matched: ["okay"], score: 2, max: 4 },
      ],
    },
  },
  { at: 28.6, kind: "pill", text: "evidence-linked rubric · 13/20", color: "#F59E0B", dur: 2.6 },
  {
    at: 29.6,
    kind: "ui",
    takeaway: "You scored thirteen of twenty. Next: set shared next steps — ask what worries her most, and agree on the plan together.",
  },
  { at: 32.5, kind: "pill", text: "voice-first rehearsal loop", color: "#22D3EE", dur: 2.6 },
  { at: 35.0, kind: "pill", text: "served by the same MCP server", color: "#34D399", dur: 2.4 },
];

export const SIMULATOR_SECONDS = 38;

const C = {
  bg: "#0B0F1A",
  panel: "#12151F",
  panel2: "#1A1F2E",
  line: "rgba(255,255,255,0.07)",
  line2: "rgba(255,255,255,0.12)",
  text: "#F4F6FB",
  muted: "#9AA6B8",
  faint: "#6B7686",
  cyan: "#22D3EE",
  green: "#34D399",
  amber: "#F59E0B",
  red: "#EF4444",
};

const FONT_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Inter', sans-serif";
const FONT_MONO = "'JetBrains Mono', 'SF Mono', Consolas, Monaco, monospace";

const ease = { damping: 14, stiffness: 160 } as const;

const popIn = (frame: number, fps: number, start: number) =>
  spring({
    frame: frame - start * fps,
    fps,
    config: ease,
    durationInFrames: Math.max(2, Math.ceil(fps * 0.5)),
  });
const fade = (frame: number, fps: number, start: number, dur = 0.4) =>
  interpolate(frame, [start * fps, (start + dur) * fps], [0, 1], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

export const SimulatorScene: React.FC = () => {
  const frame = useCurrentFrame();
  const fps = useVideoConfig().fps;
  const at = frame / fps;

  const events = simulatorEvents.filter((e) => e.at <= at);
  const windowIn = spring({ frame, fps, config: { damping: 26, stiffness: 90 }, durationInFrames: Math.ceil(0.6 * fps) });

  const logs = events.filter((e): e is LogEvent => e.kind === "log").slice(-6);
  const bubbles = events.filter((e): e is LearnerEvent | PatientEvent => e.kind === "learner" || e.kind === "patient");
  const facts = events.filter((e): e is FactEvent => e.kind === "fact");
  const rapportEvents = events.filter((e): e is RapportEvent => e.kind === "rapport");
  const rapport = rapportEvents.length ? rapportEvents[rapportEvents.length - 1].value : 0;
  const rubric = events.find((e): e is UiEvent => e.kind === "ui" && e.rubric !== undefined)?.rubric;
  const takeaway = events.find((e): e is UiEvent => e.kind === "ui" && e.takeaway !== undefined)?.takeaway;
  const selectLabel = events.find((e): e is UiEvent => e.kind === "ui" && e.select !== undefined)?.select;
  const pressed = events.some((e): e is UiEvent => e.kind === "ui" && e.pressed === true);

  const lastPatient = [...events].reverse().find((e): e is PatientEvent => e.kind === "patient");
  const lastLearner = [...events].reverse().find((e): e is LearnerEvent => e.kind === "learner");
  let orbState: "off" | "idle" | "listening" | "speaking" = "off";
  if (pressed) orbState = "idle";
  if (lastLearner && at - lastLearner.at < 1.0) orbState = "listening";
  if (lastPatient && at - lastPatient.at < 2.2) orbState = "speaking";

  const lastRapportEvent = rapportEvents.length ? rapportEvents[rapportEvents.length - 1] : null;
  const prevRapport = rapportEvents.length > 1 ? rapportEvents[rapportEvents.length - 2].value : 0;
  const needleStart = lastRapportEvent ? lastRapportEvent.at : 0;
  const needleLeft = interpolate(
    frame,
    [needleStart * fps - 4, needleStart * fps + 22],
    [((prevRapport + 3) / 6) * 100, ((rapport + 3) / 6) * 100],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const pills = simulatorEvents
    .filter((e): e is PillEvent => e.kind === "pill")
    .map((e) => ({ ...e, end: e.at + (e.dur ?? 2.4) }))
    .filter((e) => at >= e.at && at <= e.end);

  const ringRotate = (frame * 1.6) % 360;
  const orbPulse =
    orbState === "speaking" ? 1.06 + Math.sin(frame / 2.4) * 0.05 :
    orbState === "listening" ? 1.04 + Math.sin(frame / 4.5) * 0.035 :
    1 + Math.sin(frame / 30) * 0.03;

  const orbColor = orbState === "listening" ? C.green : C.cyan;
  const orbGlow = orbState === "off" ? 0 : orbState === "speaking" ? 26 : 16;

  return (
    <AbsoluteFill style={{ background: C.bg, justifyContent: "center", alignItems: "center", padding: 60, fontFamily: FONT_SANS }}>
      <div
        style={{
          width: "92%",
          maxWidth: 1720,
          height: "82%",
          opacity: windowIn,
          transform: `scale(${interpolate(windowIn, [0, 1], [0.975, 1])})`,
          borderRadius: 18,
          overflow: "hidden",
          boxShadow: "0 40px 120px rgba(0,0,0,0.65), 0 0 1px rgba(255,255,255,0.2) inset",
          background: C.panel,
          position: "relative",
          border: `1px solid ${C.line2}`,
        }}
      >
        {/* browser chrome */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "13px 18px", background: C.panel2, borderBottom: `1px solid ${C.line}` }}>
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#FF5F56" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#FFBD2E" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#27C93F" }} />
          <div
            style={{
              flex: 1, margin: "0 60px 0 24px", background: "#0E1420", border: `1px solid ${C.line}`,
              borderRadius: 999, padding: "7px 16px", color: C.faint, fontSize: 15, fontFamily: FONT_MONO,
              display: "flex", gap: 8, alignItems: "center",
            }}
          >
            <span style={{ color: C.green }}>🔒</span>
            https://9jj4zdyhu2.us-east-2.awsapprunner.com/simulator
          </div>
          <div style={{ color: C.amber, fontSize: 13, border: `1px solid rgba(245,158,11,0.4)`, borderRadius: 999, padding: "3px 12px" }}>
            educational simulation only
          </div>
        </div>

        {/* main split */}
        <div style={{ display: "grid", gridTemplateColumns: "1.32fr 1fr", height: "calc(100% - 54px)", minHeight: 0 }}>
          {/* ---------- left: voice experience ---------- */}
          <div style={{ borderRight: `1px solid ${C.line}`, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <div style={{ padding: "12px 20px", borderBottom: `1px solid ${C.line}`, color: C.muted, fontSize: 13, letterSpacing: 1.6, textTransform: "uppercase", fontWeight: 700 }}>
              Alexa+ voice experience
            </div>

            {/* orb stage */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "18px 0 6px" }}>
              <div style={{ position: "relative", width: 104, height: 104, display: "grid", placeItems: "center" }}>
                <div
                  style={{
                    position: "absolute", inset: 0, borderRadius: "50%",
                    background: `conic-gradient(from ${ringRotate}deg, transparent 0 68%, ${orbColor} 86%, transparent 100%)`,
                    WebkitMaskImage: "radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 6px))",
                    maskImage: "radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 6px))",
                    opacity: orbState === "off" ? 0 : 1,
                  }}
                />
                <div
                  style={{
                    width: 74, height: 74, borderRadius: "50%", transform: `scale(${orbState === "off" ? 0.92 : orbPulse})`,
                    backgroundImage: orbState === "off"
                      ? "radial-gradient(circle at 40% 34%, #3a4250, #232936 70%)"
                      : "radial-gradient(circle at 34% 30%, rgba(148,233,255,0.95), rgba(34,211,238,0.55) 42%, rgba(8,60,84,0.9) 78%)",
                    boxShadow: `0 0 ${orbGlow * 2}px ${orbColor}55, inset 0 0 20px rgba(255,255,255,0.22)`,
                    display: "grid", placeItems: "center",
                  }}
                >
                  <div style={{ width: 22, height: 22, borderRadius: "50%", background: "radial-gradient(circle at 40% 34%, #fff, #bdeeff 55%, transparent 75%)", opacity: orbState === "off" ? 0.3 : 0.9 }} />
                </div>
              </div>
              <div style={{ marginTop: 8, color: C.faint, fontSize: 13 }}>
                {orbState === "off" ? "start a scenario to begin" :
                 orbState === "listening" ? "listening… speak as the practitioner" :
                 orbState === "speaking" ? `patient speaking — prosody: ${lastPatient?.emotion ?? ""}` :
                 "listening for your turn"}
              </div>
            </div>

            {/* controls row: scenario select + buttons */}
            <div style={{ display: "flex", gap: 10, alignItems: "center", padding: "10px 20px", borderBottom: `1px solid ${C.line}` }}>
              <div
                style={{
                  background: C.panel2, border: `1px solid ${C.line2}`, borderRadius: 9, padding: "8px 14px",
                  color: selectLabel ? C.text : C.faint, fontSize: 15, minWidth: 300, opacity: selectLabel ? 1 : 0.55,
                                  }}
              >
                {selectLabel ?? "loading scenarios…"}
              </div>
              <div
                style={{
                  background: pressed ? "#2495ac" : "linear-gradient(180deg,#1d7f92,#14667a)", border: "1px solid #2aa4bd",
                  color: "#EAFDFF", borderRadius: 9, padding: "8px 18px", fontSize: 15, fontWeight: 600,
                }}
              >
                Start
              </div>
              <div style={{ background: C.panel2, border: `1px solid ${C.line2}`, color: C.muted, borderRadius: 9, padding: "8px 16px", fontSize: 15 }}>
                Evaluate
              </div>
              <div style={{ background: C.panel2, border: `1px solid ${C.line2}`, color: C.muted, borderRadius: 9, padding: "8px 16px", fontSize: 15 }}>
                End
              </div>
            </div>

            {/* transcript */}
            <div style={{ flex: 1, overflow: "hidden", padding: "14px 20px", display: "flex", flexDirection: "column", gap: 10, minHeight: 0 }}>
              {bubbles.map((b, i) => {
                const a = popIn(frame, fps, b.at);
                const patient = b.kind === "patient";
                return (
                  <div
                    key={`${b.at}-${i}`}
                    style={{
                      alignSelf: patient ? "flex-start" : "flex-end",
                      maxWidth: "84%", opacity: a, transform: `translateY(${interpolate(a, [0, 1], [10, 0])}px)`,
                      background: patient ? "#17202F" : "#14251D",
                      border: `1px solid ${patient ? C.line : "rgba(52,211,153,0.2)"}`,
                      borderRadius: patient ? "14px 14px 14px 4px" : "14px 14px 4px 14px",
                      padding: "10px 14px", fontSize: 16, lineHeight: 1.45, color: C.text,
                    }}
                  >
                    <div style={{ fontSize: 10.5, letterSpacing: 1.1, textTransform: "uppercase", fontWeight: 700, marginBottom: 4, color: patient ? C.cyan : C.green }}>
                      {patient ? "patient" : "you"}
                    </div>
                    {b.text}
                    {patient && (
                      <div style={{ marginTop: 6, display: "flex", gap: 6 }}>
                        <span style={{ fontSize: 11, color: C.cyan, background: "rgba(34,211,238,0.16)", border: "1px solid rgba(34,211,238,0.3)", borderRadius: 999, padding: "2px 9px", textTransform: "uppercase", letterSpacing: 0.5, fontWeight: 700 }}>
                          {b.emotion}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
              {takeaway && (
                <div
                  style={{
                    alignSelf: "flex-start", maxWidth: "94%", opacity: fade(frame, fps, 29.6, 0.5),
                    background: "rgba(52,211,153,0.10)", border: "1px solid rgba(52,211,153,0.35)",
                    borderRadius: "12px 12px 12px 4px", padding: "10px 14px", fontSize: 15, lineHeight: 1.5, color: "#D6F5E8",
                  }}
                >
                  🗣 {takeaway}
                </div>
              )}
            </div>

            {/* input row */}
            <div style={{ display: "flex", gap: 10, padding: "12px 20px 16px", borderTop: `1px solid ${C.line}`, alignItems: "center" }}>
              <div
                style={{
                  width: 42, height: 42, borderRadius: "50%", display: "grid", placeItems: "center", fontSize: 17,
                  background: orbState === "listening" ? "#0d3d31" : C.panel2,
                  border: `1px solid ${orbState === "listening" ? C.green : C.line2}`,
                  boxShadow: orbState === "listening" ? `0 0 14px ${C.green}66` : "none",
                }}
              >
                🎙
              </div>
              <div style={{ flex: 1, background: C.panel2, border: `1px solid ${C.line2}`, borderRadius: 9, padding: "10px 14px", color: C.faint, fontSize: 15 }}>
                {lastLearner && at - lastLearner.at < 1.0 ? lastLearner.text : "Ask the patient a question…"}
              </div>
              <div style={{ background: "linear-gradient(180deg,#1d7f92,#14667a)", border: "1px solid #2aa4bd", color: "#EAFDFF", borderRadius: 9, padding: "10px 18px", fontSize: 15, fontWeight: 600 }}>
                Send
              </div>
            </div>
          </div>

          {/* ---------- right: MCP inspector ---------- */}
          <div style={{ display: "flex", flexDirection: "column", minHeight: 0, fontFamily: FONT_MONO, background: "#10141F" }}>
            <div style={{ padding: "12px 18px", borderBottom: `1px solid ${C.line}`, color: C.muted, fontSize: 13, letterSpacing: 1.6, textTransform: "uppercase", fontWeight: 700 }}>
              MCP inspector <span style={{ color: C.faint, textTransform: "none", letterSpacing: 0.3, fontWeight: 400 }}>POST /mcp · session 2025-11-25</span>
            </div>

            {/* rapport meter */}
            <div style={{ padding: "14px 18px 12px", borderBottom: `1px solid ${C.line}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
                <span>patient rapport / trust</span>
                <b style={{ color: C.text, fontSize: 13 }}>+{rapport}</b>
              </div>
              <div style={{ position: "relative", height: 10, borderRadius: 6, background: "linear-gradient(90deg,#7f1d1d,#3a4250 38%,#3a4250 62%,#14532d)" }}>
                {[0, 25, 50, 75, 100].map((p) => (
                  <div key={p} style={{ position: "absolute", top: -3, left: `${p}%`, width: 1, height: 16, background: "rgba(255,255,255,0.25)" }} />
                ))}
                <div
                  style={{
                    position: "absolute", top: -5, width: 4, height: 20, borderRadius: 2, background: "#fff",
                    boxShadow: "0 0 8px rgba(255,255,255,0.6)",
                    left: `${needleLeft}%`,
                  }}
                />
              </div>
            </div>

            {/* disclosed facts */}
            <div style={{ padding: "12px 18px", borderBottom: `1px solid ${C.line}` }}>
              <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8, fontWeight: 700 }}>disclosed facts</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {facts.map((f, i) => {
                  const a = popIn(frame, fps, f.at);
                  return (
                    <span
                      key={f.id}
                      style={{
                        fontSize: 12, padding: "3px 10px", borderRadius: 6, color: "#B9F5DE",
                        background: "rgba(52,211,153,0.14)", border: "1px solid rgba(52,211,153,0.4)",
                        opacity: a, transform: `scale(${interpolate(a, [0, 1], [1.25, 1])})`,
                      }}
                    >
                      {f.id}
                    </span>
                  );
                })}
                {facts.length === 0 && <span style={{ color: C.faint, fontSize: 12 }}>facts appear as the patient discloses them</span>}
              </div>
            </div>

            {/* rubric */}
            {rubric && (
              <div style={{ padding: "12px 18px", borderBottom: `1px solid ${C.line}`, opacity: fade(frame, fps, 27.0, 0.5) }}>
                <div style={{ fontSize: 11, color: C.muted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8, fontWeight: 700 }}>
                  clinical rubric <span style={{ color: C.cyan }}>· {rubric.score} · v1.2.0</span>
                </div>
                {rubric.rows.map((row, i) => {
                  const a = fade(frame, fps, 27.2 + i * 0.12, 0.35);
                  const lit = row.matched.length > 0;
                  return (
                    <div key={row.name} style={{ display: "flex", alignItems: "center", gap: 9, padding: "5px 0", fontSize: 13, opacity: a }}>
                      <span
                        style={{
                          width: 15, height: 15, borderRadius: 4, border: `1.5px solid ${lit ? C.green : C.line2}`,
                          background: lit ? C.green : "transparent", display: "grid", placeItems: "center",
                          color: "#0B0F1A", fontSize: 11, fontWeight: 900,
                        }}
                      >
                        {lit ? "✓" : ""}
                      </span>
                      <span style={{ flex: 1, color: C.text }}>{row.name}{lit ? ` · ${row.matched.join(", ")}` : ""}</span>
                      <span style={{ width: 110, height: 6, borderRadius: 4, background: C.panel2, overflow: "hidden" }}>
                        <span
                          style={{
                            display: "block", height: "100%",
                            width: `${interpolate(frame, [(27.4 + i * 0.12) * fps, (28.2 + i * 0.12) * fps], [0, (row.score / row.max) * 100], { extrapolateRight: "clamp", extrapolateLeft: "clamp" })}%`,
                            background: "linear-gradient(90deg,#0e7490,#22D3EE)",
                          }}
                        />
                      </span>
                      <span style={{ color: C.cyan, fontWeight: 700, minWidth: 36, textAlign: "right" }}>{row.score}/{row.max}</span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* JSON-RPC log */}
            <div style={{ flex: 1, overflow: "hidden", padding: "12px 18px", display: "flex", flexDirection: "column", gap: 7, minHeight: 0 }}>
              {logs.map((e, i) => {
                const a = popIn(frame, fps, e.at);
                return (
                  <div
                    key={`${e.at}-${i}`}
                    style={{
                      fontSize: 12.5, lineHeight: 1.5, background: C.panel2, borderRadius: 7,
                      padding: "5px 10px", opacity: a, transform: `translateX(${interpolate(a, [0, 1], [-8, 0])}px)`,
                    }}
                  >
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <span style={{ color: C.green, fontWeight: 700 }}>▸</span>
                      <span style={{ color: C.cyan, fontWeight: 700 }}>{e.method}</span>
                      {e.tool && <span style={{ color: "#A5F3FC" }}>{e.tool}</span>}
                      <span style={{ color: C.faint, marginLeft: "auto" }}>{e.ms !== undefined ? `${e.ms} ms` : ""}</span>
                    </div>
                    <div style={{ color: C.muted, wordBreak: "break-all" }}>{e.args}</div>
                  </div>
                );
              })}
              {logs.length === 0 && <div style={{ color: C.faint, fontSize: 12 }}>JSON-RPC calls over Streamable HTTP appear here…</div>}
            </div>
          </div>
        </div>
      </div>

      {/* floating pills */}
      {pills.map((p, i) => {
        const life = (at - p.at) / (p.end - p.at);
        const aIn = spring({ frame: frame - p.at * fps, fps, config: { damping: 14, stiffness: 180 }, durationInFrames: Math.ceil(0.35 * fps) });
        const aOut = life > 0.82 ? interpolate(life, [0.82, 1], [1, 0], { extrapolateRight: "clamp" }) : 1;
        const alpha = Math.min(aIn, aOut);
        return (
          <div
            key={`${p.at}-${i}`}
            style={{
              position: "absolute", top: 26 + i * 64, right: 40, padding: "12px 22px", background: p.color ?? C.cyan,
              color: "#0B0F1A", borderRadius: 999, fontWeight: 700, fontSize: 21, letterSpacing: 0.2,
              opacity: alpha, transform: `translateY(${interpolate(aIn, [0, 1], [14, 0])}px)`,
              boxShadow: `0 10px 30px ${p.color ?? C.cyan}40`,
            }}
          >
            {p.text}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
