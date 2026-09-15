"""Generate the demo narration with ElevenLabs and report mux offsets.

Usage:
    export ELEVENLABS_API_KEY=sk_...
    python3 narrate.py          # writes /tmp/el_audio/seg1..seg8.mp3

Then mux onto the rendered video (offsets printed at the end):
    ffmpeg -i demo.mp4 -i /tmp/el_audio/seg1.mp3 ... (see OFFSETS below)
"""

import json, os, urllib.request, urllib.error

KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
if not KEY:
    raise SystemExit("set ELEVENLABS_API_KEY first")

VOICE = "pNInz6obpgDQGcFmaJgB"  # Adam (neutral clinician narrator)
URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}"
OUT = "/tmp/el_audio"
os.makedirs(OUT, exist_ok=True)

# (text, delay_ms) — delay is the video-time offset for ffmpeg `adelay`.
SEGMENTS = [
    ("Here's Clinical Conversation Coach. It's an MCP server that lets Alexa Plus run a safe, repeatable clinical conversation simulation.", 0),
    ("Five agent-callable tools, from scenario discovery through evaluation.", 9000),
    ("Seven authorable scenarios, from basic to advanced.", 14600),
    ("The learner hears the goal first, then the patient opens the case.", 20500),
    ("Four turns: location, radiation, shortness of breath and medications, then safety.", 31000),
    ("The rubric grades each turn, linking every score to the words that earned it. Eleven of twenty, and a spoken takeaway that tells the learner exactly what to ask next.", 63000),
    ("And when the learner dismisses the case, the safety layer pushes back: reconsider, this may delay needed care.", 76600),
    ("Alexa Plus provides the conversation. MCP provides the orchestration. The coach provides the learning outcome.", 84500),
]

for i, (text, _offset) in enumerate(SEGMENTS, 1):
    body = json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0},
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
print("""\n# assemble narration track (inputs are seg1..seg8 => indices 0..7):
# ffmpeg -i seg1.mp3 ... -i seg8.mp3 \\
#   -filter_complex "[0:a]...adelay=0:all=1[a1];[1:a]...adelay=9000:all=1[a2];...;[a1][a2]...[a8]amix=inputs=8:duration=longest:normalize=0,apad" \\
#   -t 93.2 -ar 48000 -ac 2 narration.wav
# then: ffmpeg -i demo.mp4 -i narration.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest out.mp4""")