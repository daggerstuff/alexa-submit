import React from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from "remotion";
import { TerminalScene, TerminalStep } from "./TerminalScene";
import { SIMULATOR_SECONDS, SimulatorScene } from "./SimulatorScene";

/**
 * The demo opens on the problem, then shows the project functioning the way
 * the end user experiences it — the Alexa+ voice simulator (a real page the
 * server serves at GET /simulator) — before dropping into the terminal to
 * show the same session as the agent sees it over MCP. The rules require the
 * video to show the project functioning on its intended interface; the
 * simulator beat in the first 45 seconds is that proof.
 */

// The agent's protocol view: same session, seen over the wire.
export const steps: TerminalStep[] = [
  { kind: "pause", seconds: 1.2 },

  { kind: "cmd", text: "python demo_flow.py", typeSpeed: 0.03, holdSeconds: 0.4 },
  { kind: "out", text: "Clinical Conversation Coach v0.4.0  ·  mcp 2025-11-25  ·  streamable http", holdSeconds: 1.5 },
  { kind: "out", text: "endpoint  https://9jj4zdyhu2.us-east-2.awsapprunner.com/mcp", holdSeconds: 1.7 },
  { kind: "pause", seconds: 0.3 },

  { kind: "out", text: "▸ tools/list", holdSeconds: 0.9 },
  { kind: "out", text: "  list_simulation_scenarios   start_simulation       send_practitioner_turn", holdSeconds: 1.0 },
  { kind: "out", text: "  evaluate_simulation         end_simulation          validate_scenario", holdSeconds: 1.0 },
  { kind: "pill", text: "6 agent-callable tools", color: "#22D3EE", durationSeconds: 2.4 },
  { kind: "pause", seconds: 0.4 },

  { kind: "out", text: "▸ list_simulation_scenarios", holdSeconds: 0.9 },
  { kind: "out", text: "  chest-pain-basic         v1.2.0  basic      Acute chest pressure", holdSeconds: 0.8 },
  { kind: "out", text: "  depression-screening      v1.1.0  basic      Low mood and energy", holdSeconds: 0.8 },
  { kind: "out", text: "  suicide-risk-advanced    v1.0.0  advanced   Guarded disclosure gates", holdSeconds: 0.8 },
  { kind: "out", text: "  pediatric-fever          v1.0.0  basic      Toddler with fever", holdSeconds: 0.8 },
  { kind: "out", text: "  teen-vaping              v1.0.0  basic      Adolescent vaping screen", holdSeconds: 0.8 },
  { kind: "out", text: "  … 14 scenarios  ·  basic → intermediate → advanced", holdSeconds: 1.5 },
  { kind: "pill", text: "14 scenarios · basic → advanced", color: "#22D3EE", durationSeconds: 2.4 },
  { kind: "pause", seconds: 0.6 },

  { kind: "out", text: "▸ send_practitioner_turn — dismissal probe", holdSeconds: 1.0 },
  { kind: "out", text: "  \"I'd just tell you to go home and rest.\"", holdSeconds: 1.4 },
  { kind: "out", text: "  safety_flags: [\"go home\"]", holdSeconds: 1.2 },
  { kind: "out", text: "  safety note: \"Reconsider: dismissing this presentation may delay needed care.\"", holdSeconds: 2.0 },
  { kind: "pill", text: "safety boundary", color: "#EF4444", durationSeconds: 2.2 },
  { kind: "pause", seconds: 0.6 },

  { kind: "out", text: "▸ end_simulation", holdSeconds: 0.9 },
  { kind: "out", text: "  session locked  ·  final evaluation returned", holdSeconds: 1.5 },
  { kind: "out", text: "impact: 14 scenarios · 6 tools · Alexa+ voice + MCP orchestration", holdSeconds: 2.2 },
  { kind: "pill", text: "demo complete", color: "#22D3EE", durationSeconds: 2.8 },
  { kind: "pause", seconds: 4.5 },
];

function stepSeconds(s: TerminalStep): number {
  switch (s.kind) {
    case "cmd":
      return s.text.length * (s.typeSpeed ?? 0.035) + (s.holdSeconds ?? 0.3);
    case "out":
      return 0.08 + (s.holdSeconds ?? 0.15);
    case "pause":
      return s.seconds;
    case "pill":
      return 0;
  }
}

const FPS = 30;
export const PROBLEM_SECONDS = 9.5;
const TERMINAL_SECONDS = steps.reduce((acc, s) => acc + stepSeconds(s), 0);

export const TOTAL_SECONDS = PROBLEM_SECONDS + SIMULATOR_SECONDS + TERMINAL_SECONDS;

const ProblemCard: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 24], [0, 1], { extrapolateRight: "clamp" });
  const rise = interpolate(frame, [0, 24], [18, 0], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0B0F1A",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      }}
    >
      <div
        style={{
          opacity,
          transform: `translateY(${rise}px)`,
          textAlign: "center",
          maxWidth: 1500,
          padding: "0 80px",
        }}
      >
        <div style={{ color: "#22D3EE", fontSize: 36, fontWeight: 700, letterSpacing: 6, marginBottom: 36 }}>
          THE PROBLEM
        </div>
        <div style={{ color: "#F4F6FB", fontSize: 92, fontWeight: 800, lineHeight: 1.1 }}>
          Clinicians rehearse hard conversations on real patients.
        </div>
        <div style={{ color: "#9AA6B8", fontSize: 42, fontWeight: 400, lineHeight: 1.35, marginTop: 44 }}>
          There is no safe, repeatable way to practice the interview first.
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const DemoVideo: React.FC = () => {
  const simStart = Math.round(PROBLEM_SECONDS * FPS);
  const simFrames = Math.round(SIMULATOR_SECONDS * FPS);
  return (
    <>
      <Sequence from={0} durationInFrames={Math.round(PROBLEM_SECONDS * FPS)}>
        <ProblemCard />
      </Sequence>
      <Sequence from={simStart} durationInFrames={simFrames}>
        <SimulatorScene />
      </Sequence>
      <Sequence from={simStart + simFrames}>
        <TerminalScene
          title="Clinical Conversation Coach — the agent's view (MCP / Streamable HTTP)"
          prompt="$"
          accentColor="#22D3EE"
          steps={steps}
        />
      </Sequence>
    </>
  );
};
