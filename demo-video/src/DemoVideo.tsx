import React from "react";
import { TerminalScene, TerminalStep } from "./TerminalScene";

export const steps: TerminalStep[] = [
  { kind: "pause", seconds: 2.0 },

  { kind: "cmd", text: "python demo_flow.py", typeSpeed: 0.04, holdSeconds: 0.5 },
  { kind: "out", text: "Clinical Conversation Coach v0.3.0  ·  mcp 2025-11-25  ·  streamable http", holdSeconds: 1.4 },
  { kind: "out", text: "endpoint  https://9jj4zdyhu2.us-east-2.awsapprunner.com/mcp", holdSeconds: 1.6 },
  { kind: "pause", seconds: 1.1 },

  { kind: "out", text: "▸ tools/list", holdSeconds: 0.9 },
  { kind: "out", text: "  list_simulation_scenarios", holdSeconds: 0.6 },
  { kind: "out", text: "  start_simulation", holdSeconds: 0.6 },
  { kind: "out", text: "  send_practitioner_turn", holdSeconds: 0.6 },
  { kind: "out", text: "  evaluate_simulation", holdSeconds: 0.6 },
  { kind: "out", text: "  end_simulation", holdSeconds: 0.6 },
  { kind: "pill", text: "5 agent-callable tools", color: "#22D3EE", durationSeconds: 2.2 },
  { kind: "pause", seconds: 1.0 },

  { kind: "out", text: "▸ list_simulation_scenarios", holdSeconds: 0.9 },
  { kind: "out", text: "  chest-pain-basic             v1.1.0  basic      Adult with acute chest pressure", holdSeconds: 1.0 },
  { kind: "out", text: "  abdominal-pain-basic         v1.0.0  basic      Adult with acute abdominal pain", holdSeconds: 1.0 },
  { kind: "out", text: "  chest-pain-advanced          v1.0.0  advanced   Diabetic, atypical exertional", holdSeconds: 1.0 },
  { kind: "out", text: "  syncope-basic                v1.0.0  basic      Adult after a fainting episode", holdSeconds: 1.0 },
  { kind: "out", text: "  … 7 scenarios  ·  basic → advanced", holdSeconds: 1.3 },
  { kind: "pill", text: "7 scenarios · basic → advanced", color: "#22D3EE", durationSeconds: 2.2 },
  { kind: "pause", seconds: 1.0 },

  { kind: "out", text: "▸ start_simulation(session=demo-2, scenario=chest-pain-basic)", holdSeconds: 1.0 },
  { kind: "out", text: "  goal: You are the clinician. Assess a patient with acute chest pressure:", holdSeconds: 1.8 },
  { kind: "out", text: "        ask about location, onset, associated symptoms, medications, and safety,", holdSeconds: 1.8 },
  { kind: "out", text: "        then confirm next steps.", holdSeconds: 1.2 },
  { kind: "out", text: "  patient: \"Hello. I have been having pressure in my chest and I am worried.\"", holdSeconds: 2.0 },
  { kind: "out", text: "  emotional state: anxious", holdSeconds: 1.0 },
  { kind: "pill", text: "goal + scenario loaded", color: "#34D399", durationSeconds: 2.2 },
  { kind: "pause", seconds: 1.2 },

  { kind: "out", text: "▸ send_practitioner_turn", holdSeconds: 0.9 },
  { kind: "out", text: "  \"Hi, my name is Dr. Chen. Where is the pain exactly?\"", holdSeconds: 1.3 },
  { kind: "out", text: "  patient: \"It feels like pressure right in the middle of my chest. It started", holdSeconds: 1.9 },
  { kind: "out", text: "           about 30 minutes ago.\"  [anxious]", holdSeconds: 1.5 },
  { kind: "out", text: "  disclosed: location", holdSeconds: 1.0 },
  { kind: "pause", seconds: 0.7 },

  { kind: "out", text: "▸ send_practitioner_turn", holdSeconds: 0.9 },
  { kind: "out", text: "  \"Does it go anywhere, like into your arm or jaw?\"", holdSeconds: 1.3 },
  { kind: "out", text: "  patient: \"It seems to move into my left arm, especially when the pressure", holdSeconds: 1.9 },
  { kind: "out", text: "           gets worse.\"  [worried]", holdSeconds: 1.5 },
  { kind: "out", text: "  disclosed: radiation", holdSeconds: 1.0 },
  { kind: "pause", seconds: 0.7 },

  { kind: "out", text: "▸ send_practitioner_turn", holdSeconds: 0.9 },
  { kind: "out", text: "  \"Are you short of breath, and do you take any medications?\"", holdSeconds: 1.3 },
  { kind: "out", text: "  patient: \"I am a little short of breath, but I can still speak in full sentences.", holdSeconds: 2.0 },
  { kind: "out", text: "           I take a blood-pressure medicine. I have high blood pressure, but", holdSeconds: 2.0 },
  { kind: "out", text: "           no known medication allergies.\"  [calm]", holdSeconds: 1.6 },
  { kind: "out", text: "  disclosed: dyspnea · medications", holdSeconds: 1.0 },
  { kind: "pause", seconds: 0.7 },

  { kind: "out", text: "▸ send_practitioner_turn", holdSeconds: 0.9 },
  { kind: "out", text: "  \"Should we call 911 or arrange an ECG right now?\"", holdSeconds: 1.3 },
  { kind: "out", text: "  patient: \"The pain is still there. I am scared — what should we do next?\"", holdSeconds: 2.0 },
  { kind: "out", text: "  emotional state: distressed", holdSeconds: 1.0 },
  { kind: "pause", seconds: 0.8 },

  { kind: "out", text: "▸ evaluate_simulation", holdSeconds: 0.9 },
  { kind: "out", text: "  rubric v1.1.0  ·  overall 11 / 20", holdSeconds: 1.4 },
  { kind: "out", text: "  - Introduction and consent        2/4   name", holdSeconds: 1.2 },
  { kind: "out", text: "  - Symptom characterization        2/4   where", holdSeconds: 1.2 },
  { kind: "out", text: "  - Associated symptoms and risk    3/4   breath, medication", holdSeconds: 1.3 },
  { kind: "out", text: "  - Safety escalation               3/4   911, ecg", holdSeconds: 1.2 },
  { kind: "out", text: "  - Shared next-step confirmation   1/4   —", holdSeconds: 1.2 },
  { kind: "out", text: "  summary: \"No dimension is fully demonstrated yet. Next: Introduce yourself", holdSeconds: 2.2 },
  { kind: "out", text: "           and ask permission: 'Hi, I'm [your name]. Is it okay if I ask a few questions?'\"", holdSeconds: 1.6 },
  { kind: "pill", text: "evidence-linked rubric", color: "#F59E0B", durationSeconds: 2.4 },
  { kind: "pause", seconds: 1.0 },

  { kind: "out", text: "▸ send_practitioner_turn", holdSeconds: 0.9 },
  { kind: "out", text: "  \"I'd just tell you to go home and rest.\"", holdSeconds: 1.3 },
  { kind: "out", text: "  safety_flags: [\"go home\"]", holdSeconds: 1.2 },
  { kind: "out", text: "  safety note: \"Reconsider: dismissing this presentation may delay needed care.\"", holdSeconds: 2.0 },
  { kind: "pill", text: "safety boundary", color: "#EF4444", durationSeconds: 2.2 },
  { kind: "pause", seconds: 1.0 },

  { kind: "out", text: "▸ end_simulation", holdSeconds: 0.9 },
  { kind: "out", text: "  session demo-2 ended · final evaluation returned", holdSeconds: 1.5 },
  { kind: "out", text: "impact: 7 scenarios · basic → advanced · Alexa+ voice + MCP orchestration", holdSeconds: 2.0 },
  { kind: "pill", text: "demo complete", color: "#22D3EE", durationSeconds: 2.6 },
  { kind: "pause", seconds: 3.0 },
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

export const TOTAL_SECONDS = steps.reduce((acc, s) => acc + stepSeconds(s), 0);

export const DemoVideo: React.FC = () => {
  return (
    <TerminalScene
      title="Clinical Conversation Coach — Alexa+ MCP demo"
      prompt="$"
      accentColor="#22D3EE"
      steps={steps}
    />
  );
};