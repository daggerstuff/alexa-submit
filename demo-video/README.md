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

## Note

The content is scripted from the deterministic engine output (not live LLM calls),
so rendering needs no network or API key. Audio is silent; add a narration track in
`DemoVideo.tsx` if a voice-over is wanted.