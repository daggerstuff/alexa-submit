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

- `src/DemoVideo.tsx` — the demo script: a `TerminalStep` timeline showing
  `tools/list`, the scenario library, the chest-pain conversation, the graded
  evaluation (11/20 + spoken summary), and the dismissal safety boundary.
- `src/TerminalScene.tsx` — the animated terminal component (from
  `calesthio/openmontage` `remotion-composer`, with `import React` prepended).

## Narration (ElevenLabs)

The render is silent; the voice-over is generated separately and muxed on top.

```bash
export ELEVENLABS_API_KEY=sk_...
python3 narrate.py            # writes /tmp/el_audio/seg1..seg8.mp3 + prints offsets
# assemble:  ffmpeg -i seg1.mp3 ... -i seg8.mp3 -filter_complex "adelay/amix/apad" -t 93.2 narration.wav
# mux:       ffmpeg -i demo.mp4 -i narration.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest out.mp4
```

The API key is never committed; it is read from the environment only.

## Note

The content is scripted from the deterministic engine output (not live LLM calls),
so rendering needs no network or API key. The narration is an ElevenLabs "Adam"
voice over the eight demo beats.