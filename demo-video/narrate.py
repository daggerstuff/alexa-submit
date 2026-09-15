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

import json, os, urllib.request, urllib.error

KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
if not KEY:
    raise SystemExit("set ELEVENLABS_API_KEY first")

VOICE = "pNInz6obpgDQGcFmaJgB"  # Adam (neutral clinician narrator)
URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}"
OUT = "/tmp/el_audio9"
os.makedirs(OUT, exist_ok=True)

PROBLEM_SECONDS = 9.5  # keep in sync with DemoVideo.tsx
SHIFT = int(PROBLEM_SECONDS * 1000)

# (text, delay_ms) — delay is the video-time offset for ffmpeg `adelay`.
SEGMENTS = [
    ("Practicing a difficult patient conversation usually means doing it live — on a real patient. There is no safe way to rehearse the interview first.", 0),
    ("Here's Clinical Conversation Coach. An M-C-P server that lets Alexa Plus run safe, repeatable clinical-conversation practice.", SHIFT + 0),
    ("Five agent-callable tools — from scenario discovery, through evaluation.", SHIFT + 9300),
    ("Seven authorable scenarios... from basic, to advanced.", SHIFT + 15200),
    ("The learner hears the goal first... then the patient opens the case.", SHIFT + 20500),
    ("Four turns: location, radiation, shortness of breath and medications — then safety.", SHIFT + 31000),
    ("The rubric grades every turn, linking each score to the words that earned it. Eleven of twenty... with a spoken takeaway that tells the learner exactly what to ask next.", SHIFT + 63000),
    ("And when the learner dismisses the case, the safety layer pushes back: reconsider — this may delay needed care.", SHIFT + 75500),
    ("Alexa Plus provides the conversation. M-C-P provides the orchestration. And the coach... provides the learning outcome.", SHIFT + 83300),
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
#   -t <total> -ar 48000 -ac 2 narration.wav
# then: ffmpeg -i demo.mp4 -i narration.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest out.mp4""")