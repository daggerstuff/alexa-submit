# Demo video renderer (Remotion)

Renders the demo video as a synthetic terminal recording — the same approach that
produced the original `demo.mp4`. The mp4 output is gitignored (`*.mp4`); only this
source is committed so the video is reproducible.

## Render

```bash
cd demo-video
npm install
npx remotion render src/index.ts DemoVideo out/demo.mp4 --codec h264
cp out/demo.mp4 ../demo-v2.mp4
```

## Structure

- `src/DemoVideo.tsx` — the demo script. It opens with a **problem-first title
  card** (`THE PROBLEM`: "Clinicians rehearse hard conversations on real
  patients."), then a `TerminalStep` timeline showing `tools/list`, the scenario
  library, the chest-pain conversation, the graded evaluation (11/20 + spoken
  summary), and the dismissal safety boundary. `PROBLEM_SECONDS` (9.5) is the
  length of the opening card; the terminal starts immediately after.
- `src/TerminalScene.tsx` — the animated terminal component (from
  `calesthio/openmontage` `remotion-composer`, with `import React` prepended).

## Narration (ElevenLabs)

The render is silent; the voice-over is generated separately and muxed on top.
The opening beat leads with the problem; the terminal beats are shifted by
`PROBLEM_SECONDS` accordingly.

```bash
export ELEVENLABS_API_KEY=sk_...
python3 narrate.py            # writes /tmp/el_audio9/seg1..seg9.mp3 + prints offsets
# assemble:  ffmpeg -i seg1.mp3 ... -i seg9.mp3 -filter_complex "adelay/amix/apad" -t 102.6 narration.wav
# mux:       ffmpeg -i demo.mp4 -i narration.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest out.mp4
```

The API key is never committed; it is read from the environment only. The
narration uses the **Eleven v3** model (recommended for video narration), Natural
stability, and speech-normalized text ("M-C-P" spelled out, ellipses for pacing).

## Note

The content is scripted from the deterministic engine output (not live LLM calls),
so rendering needs no network or API key. The narration is an ElevenLabs "Adam"
voice over nine beats: a problem-first opening, then the eight terminal beats.