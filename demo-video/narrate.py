"""Generate the demo narration with ElevenLabs and report mux offsets.

Uses the Eleven v3 model (recommended for video narration) with a neutral
"Adam" voice, Natural stability, and speech-normalized text (M-C-P spelled
out, ellipses for pacing, em-dash for emphasis).

The opening beat leads with the problem; the terminal starts at
PROBLEM_SECONDS (9.5s) in DemoVideo.tsx, so every terminal-beat offset below
is shifted by +9500 ms.

Usage:
    export ELEVENLABS_API_KEY=sk_...
    python3 narrate.py          # writes /tmp/el_audio9/seg1..seg9.mp3

Then mux onto the rendered video (offsets printed at the end).
"""

import json
import os
import urllib.error
import urllib.request

KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
if not KEY:
    raise SystemExit("set ELEVENLABS_API_KEY first")

VOICE = "pNInz6obpgDQGcFmaJgB"  # Adam (neutral clinician narrator)
URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}"
OUT = "/tmp/el_audio9"
os.makedirs(OUT, exist_ok=True)

PROBLEM_SECONDS = 9.5   # keep in sync with DemoVideo.tsx
SIMULATOR_SECONDS = 38.0  # keep in sync with SimulatorScene.tsx

# (text, delay_ms) — delay is the absolute video-time offset for ffmpeg `adelay`.
# Cues are locked to the beat times in DemoVideo.tsx / SimulatorScene.tsx:
#   0s problem card · 9.5s simulator scene (voice experience, rapport, rubric)
#   47.5s terminal scene (agent's protocol view: tools, scenarios, safety, end).
SEGMENTS = [
    # 0.0s — problem card
    ("Practicing a difficult patient conversation usually means doing it live — on a real patient. There is no safe way to rehearse the interview first.", 0),
    # 9.5s — simulator scene: page, scenario, start, opening line
    ("Practice needs a voice. This is the Alexa Plus experience: the same M-C-P server, with a multimodal simulator any learner can open in a browser. Pick a scenario... and press start.", 9500),
    # 19.5s — the four practitioner turns, tool calls, facts, rapport meter
    ("Every turn is a live M-C-P tool call. The patient answers with emotional inflection... while the inspector shows the protocol traffic, the facts she discloses, and a trust meter that moves with the learner's warmth.", 19500),
    # 33.5s — evaluate_simulation + rubric checkboxes + spoken takeaway
    ("Then the rubric: every dimension scored, linked to the words that earned each point — and a spoken takeaway for exactly what to ask next.", 33500),
    # 41.5s — disclaimer chip + closing hold on the simulator
    ("Educational only. A safe, repeatable rehearsal — every single time.", 41500),
    # 47.5s — terminal scene: protocol view begins
    ("Under the hood, the agent sees the same session as pure protocol: initialize... tool discovery... tool calls — M-C-P twenty twenty-five, over streamable H-T-T-P.", 47500),
    # 54.0s — tools/list + scenario library
    ("Six agent-callable tools. Fourteen authorable scenarios — basic, through advanced.", 54000),
    # 62.5s — the dismissal safety boundary
    ("And the runtime keeps a boundary: dismiss the case — go home and rest — and the coach pushes back. Reconsider... this may delay needed care.", 62500),
    # 71.0s — closing line
    ("Alexa Plus provides the conversation. M-C-P provides the orchestration. And the coach... provides the learning outcome.", 71000),
]

for i, (text, _offset) in enumerate(SEGMENTS, 1):
    body = json.dumps({
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
            "speed": 1.0,
        },
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "xi-api-key": KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    })
    path = f"{OUT}/seg{i}.mp3"
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        open(path, "wb").write(data)
        print(f"seg{i}: {len(data)} bytes")
    except urllib.error.HTTPError as e:
        print(f"seg{i}: HTTP {e.code} {e.read().decode()[:300]}")
    except Exception as e:
        print(f"seg{i}: ERROR {type(e).__name__} {e}")

print("\n# mux offsets (ms) for ffmpeg adelay:")
for i, (_text, offset) in enumerate(SEGMENTS, 1):
    print(f"  seg{i}: {offset}")
print("""\n# assemble narration track (inputs seg1..seg9 => indices 0..8):
# ffmpeg -i seg1.mp3 ... -i seg9.mp3 \\
#   -filter_complex "[0:a]...adelay=0:all=1[a1];[1:a]...adelay=9500:all=1[a2];...;[a1]...[a9]amix=inputs=9:duration=longest:normalize=0,apad" \\
#   -t 80.3 -ar 48000 -ac 2 narration.wav
# then: ffmpeg -i demo.mp4 -i narration.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest out.mp4
# (total video duration is exported by DemoVideo.tsx: PROBLEM 9.5s + SIMULATOR 38s + TERMINAL ~32.8s = ~80.3s)""")
