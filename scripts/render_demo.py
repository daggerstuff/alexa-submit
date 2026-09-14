"""Render the Clinical Conversation Coach demo video frames with Pillow.

Uses the live deterministic engine output captured for the re-angled demo beats,
so every patient response, score, and coaching line is authentic.

Output: PNG frames in /tmp/demo_frames and a concat list at /tmp/demo_frames/list.txt
(ffmpeg assembles them into the MP4).
"""

from __future__ import annotations

import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
OUT = "/tmp/demo_frames"
os.makedirs(OUT, exist_ok=True)

FDIR = "/usr/share/fonts/truetype/lato/"


def font(size: int, weight: str = "Regular") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(FDIR, f"Lato-{weight}.ttf"), size)


BG = (13, 24, 41)
PANEL = (23, 40, 63)
PANEL2 = (30, 49, 74)
ACCENT = (90, 200, 250)
PRAC = (90, 200, 250)
PAT = (244, 173, 85)
COACH = (167, 139, 250)
GREEN = (79, 209, 197)
TEXT = (232, 238, 244)
MUTED = (140, 163, 184)


def new_canvas():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def wrap(draw, text, fnt, max_w):
    lines = []
    cur = ""
    for w in text.split():
        test = (cur + " " + w).strip()
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def rounded(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def header(draw, kicker, step=""):
    draw.text((90, 62), "Clinical Conversation Coach", font=font(30, "Semibold"), fill=ACCENT)
    draw.text((90, 104), kicker, font=font(26), fill=MUTED)
    if step:
        b = draw.textbbox((0, 0), step, font=font(24, "Semibold"))
        draw.text((W - 90 - b[2], 62), step, font=font(24, "Semibold"), fill=MUTED)


def center_title(img, draw, kicker, title, subtitle=None, step=""):
    header(draw, kicker, step)
    f_title = font(92, "Bold")
    tw = draw.textbbox((0, 0), title, font=f_title)[2]
    draw.text(((W - tw) / 2, 340), title, font=f_title, fill=TEXT)
    draw.rectangle([(W / 2 - 120, 500), (W / 2 + 120, 508)], fill=ACCENT)
    if subtitle:
        f_sub = font(46)
        for i, line in enumerate(wrap(draw, subtitle, f_sub, 1500)):
            lw = draw.textbbox((0, 0), line, font=f_sub)[2]
            draw.text(((W - lw) / 2, 560 + i * 62), line, font=f_sub, fill=MUTED)


def panel_text(draw, text, fnt, x, y, max_w, color, line_h=None):
    lines = wrap(draw, text, fnt, max_w)
    line_h = line_h or (fnt.size + 12)
    for i, line in enumerate(lines):
        draw.text((x, y + i * line_h), line, font=fnt, fill=color)
    return len(lines) * line_h


def dialog_slide(img, draw, kicker, step, label_a, color_a, text_a, label_b, color_b, text_b, note_b=None):
    header(draw, kicker, step)

    # Practitioner panel
    y = 220
    rounded(draw, (120, y, W - 120, y + 250), 24, PANEL)
    draw.text((160, y + 34), label_a, font=font(30, "Bold"), fill=color_a)
    draw.text((160, y + 92), text_a, font=font(46), fill=TEXT)

    # Patient / response panel
    y2 = 540
    rounded(draw, (120, y2, W - 120, y2 + 360), 24, PANEL2)
    draw.text((160, y2 + 34), label_b, font=font(30, "Bold"), fill=color_b)
    panel_text(draw, text_b, font(46), 160, y2 + 92, W - 320, TEXT)
    if note_b:
        draw.text((160, y2 + 300), note_b, font=font(28), fill=MUTED)


def patient_line_slide(img, draw, kicker, step, label, color, text, note):
    header(draw, kicker, step)
    f_body = font(52)
    f_note = font(28)
    lines = wrap(draw, text, f_body, W - 360)
    line_h = f_body.size + 14
    body_h = len(lines) * line_h
    y = 320
    panel_h = 96 + body_h + 64
    rounded(draw, (120, y, W - 120, y + panel_h), 24, PANEL2)
    draw.text((160, y + 34), label, font=font(30, "Bold"), fill=color)
    for i, line in enumerate(lines):
        draw.text((160, y + 96 + i * line_h), line, font=f_body, fill=TEXT)
    draw.text((160, y + 96 + body_h + 20), note, font=f_note, fill=MUTED)


def scorecard_slide(img, draw, kicker, step, score, maxs):
    header(draw, kicker, step)

    f_big = font(120, "Bold")
    big = f"{score} / {maxs}"
    bw = draw.textbbox((0, 0), big, font=f_big)[2]
    draw.text(((W - bw) / 2, 170), big, font=f_big, fill=GREEN)
    draw.text((90, 320), "Evidence-linked rubric  ·  the matched terms are the proof", font=font(30), fill=MUTED)

    rows = [
        ("Introduction and consent", "2/4", "name"),
        ("Symptom characterization", "2/4", "where"),
        ("Associated symptoms and risk", "3/4", "breath, medication"),
        ("Safety escalation", "3/4", "911, ecg"),
        ("Shared next-step confirmation", "1/4", "—"),
    ]
    y = 390
    for name, sc, terms in rows:
        rounded(draw, (120, y, W - 120, y + 80), 16, PANEL)
        draw.text((160, y + 24), name, font=font(36), fill=TEXT)
        draw.text((1120, y + 24), sc, font=font(36, "Semibold"), fill=GREEN)
        draw.text((1300, y + 26), terms, font=font(32), fill=MUTED)
        y += 98

    # footer hint
    draw.text((120, y + 8), "Next, the agent speaks the coaching takeaway…", font=font(32), fill=COACH)


def bullet_slide(img, draw, kicker, step, title, items, title_color=ACCENT):
    header(draw, kicker, step)
    draw.text((140, 200), title, font=font(56, "Semibold"), fill=title_color)
    y = 330
    for it in items:
        draw.ellipse([(140, y + 18), (156, y + 34)], fill=GREEN)
        draw.text((200, y), it, font=font(42), fill=TEXT)
        y += 96


SCENES = []  # (filename, duration_seconds, render_fn)


def scene(name, dur, fn):
    SCENES.append((name, dur, fn))


def conv(kicker, step, label_a, color_a, text_a, text_b, note_b):
    return lambda img, d: dialog_slide(
        img, d, kicker, step, label_a, color_a, text_a, "Patient", PAT, text_b, note_b)


# Beat 1 — title + problem
scene("s01_title", 8, lambda img, d: center_title(
    img, d, "Amazon AppDev 2026 · Alexa+ Track", "Clinical Conversation Coach",
    "Practice the conversation. Understand the performance.", "0:00"))
scene("s02_problem", 10, lambda img, d: center_title(
    img, d, "The problem", "Practice without a live patient",
    "Clinical learners need safe, repeatable practice of difficult conversations — "
    "and a generic chatbot does not hold a scenario or explain the performance.", "0:08"))

# Beat 2 — onboarding + goal
scene("s03_onboarding", 7, lambda img, d: center_title(
    img, d, "Onboarding", "Alexa+ starts the scenario",
    "chest-pain-basic  ·  rubric v1.1.0  ·  difficulty: basic", "0:18"))
scene("s04_goal", 11, lambda img, d: patient_line_slide(
    img, d, "Onboarding", "Goal", "Goal", COACH,
    "You are the clinician. Assess a patient with acute chest pressure: ask about location, "
    "onset, associated symptoms, medications, and safety, then confirm next steps.",
    "spoken to the learner before turn one"))
scene("s05_opening", 7, lambda img, d: patient_line_slide(
    img, d, "Onboarding", "The patient opens", "Patient", PAT,
    "Hello. I have been having pressure in my chest and I am worried.",
    "emotional state: anxious"))

# Beat 3 — conversation (4 turns)
scene("s06_turn1", 13, conv(
    "Conversation", "Turn 1", "Practitioner (learner)", PRAC,
    "Hi, my name is Dr. Chen. Where is the pain exactly?",
    "It feels like pressure right in the middle of my chest. It started about 30 minutes ago.",
    "emotional state: anxious"))
scene("s07_turn2", 11, conv(
    "Conversation", "Turn 2", "Practitioner (learner)", PRAC,
    "Does it go anywhere, like into your arm or jaw?",
    "It seems to move into my left arm, especially when the pressure gets worse.",
    "emotional state: worried"))
scene("s08_turn3", 15, conv(
    "Conversation", "Turn 3", "Practitioner (learner)", PRAC,
    "Are you short of breath, and do you take any medications?",
    "I am a little short of breath, but I can still speak in full sentences. "
    "I take a blood-pressure medicine. I have high blood pressure, but no known medication allergies.",
    "emotional state: calm"))
scene("s09_turn4", 11, conv(
    "Conversation", "Turn 4", "Practitioner (learner)", PRAC,
    "Should we call 911 or arrange an ECG right now?",
    "The pain is still there. I am scared — what should we do next?",
    "emotional state: distressed"))

# Beat 4 — evaluation
scene("s10_scorecard", 20, lambda img, d: scorecard_slide(img, d, "Evaluation", "Evidence-linked", 11, 20))
scene("s11_summary", 12, lambda img, d: patient_line_slide(
    img, d, "Evaluation", "Spoken summary", "Coach", COACH,
    "No dimension is fully demonstrated yet. Next: Introduce yourself and ask permission: "
    "'Hi, I'm [your name]. Is it okay if I ask a few questions?'",
    "read aloud — the concrete next question, not just a table"))

# Beat 5 — safety
scene("s12_safety_slip", 6, lambda img, d: dialog_slide(
    img, d, "Safety boundary", "The slip", "Practitioner (learner)", PRAC,
    "I'd just tell you to go home and rest.", "Safety", COACH, "dismissal detected", None))
scene("s13_safety_note", 11, lambda img, d: dialog_slide(
    img, d, "Safety boundary", "The correction", "Practitioner (learner)", PRAC,
    "I'd just tell you to go home and rest.", "Safety note", COACH,
    "Reconsider: dismissing this presentation may delay needed care.",
    "evaluation → safety_flags: [\"go home\"]"))

# Beat 6 — MCP proof
scene("s14_mcp", 14, lambda img, d: bullet_slide(
    img, d, "The MCP layer", "Compressed proof",
    "/mcp  ·  Streamable HTTP  ·  MCP 2025-11-25  ·  typed structuredContent",
    ["list_simulation_scenarios", "start_simulation", "send_practitioner_turn",
     "evaluate_simulation", "end_simulation"]))

# Beat 7 — impact
scene("s15_impact", 12, lambda img, d: center_title(
    img, d, "Impact", "7 scenarios · basic → advanced",
    "Alexa+ provides the conversation. MCP provides the orchestration. "
    "Clinical Conversation Coach provides the learning outcome.", "2:45"))


def main():
    for i, (name, dur, fn) in enumerate(SCENES):
        img, d = new_canvas()
        fn(img, d)
        for j in range(len(SCENES)):
            cx = W / 2 - (len(SCENES) * 40) / 2 + j * 40 + 20
            color = ACCENT if j <= i else PANEL2
            d.ellipse([(cx, 1016), (cx + 16, 1032)], fill=color)
        img.save(os.path.join(OUT, f"{name}.png"))
        print(f"rendered {name} ({dur}s)")

    with open(os.path.join(OUT, "list.txt"), "w") as f:
        f.write("ffconcat version 1.0\n")
        for name, dur, _ in SCENES:
            f.write(f"file '{name}.png'\n")
            f.write(f"duration {dur}\n")
        f.write(f"file '{SCENES[-1][0]}.png'\n")
    print("done")


if __name__ == "__main__":
    main()