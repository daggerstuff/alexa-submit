# Demo video renderer (Remotion)

Renders the demo video as a synthetic screen recording — the same approach that
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
  patients."), then shows the project functioning on its intended interface:
  a **simulated Alexa+ voice experience** (`SimulatorScene` — the browser page
  the server serves at `GET /simulator`): four spoken practitioner turns, the
  rapport meter moving with the learner's warmth, disclosed facts lighting up,
  and the graded rubric (13/20 + spoken takeaway). It then drops into the
  terminal for the agent's protocol view (`TerminalScene`): the endpoint,
  `tools/list`, the 14-scenario library, the dismissal safety boundary, and
  `end_simulation`. `PROBLEM_SECONDS` (9.5) and `SIMULATOR_SECONDS` (38) drive
  the sequence offsets; total render ≈ 1:20.
- `src/SimulatorScene.tsx` — the multimodal Alexa+ experience, synthesized
  from one event timeline (`simulatorEvents`): every spoken turn visibly
  drives a `tools/call` in the MCP inspector pane, so the voice experience and
  the protocol traffic animate together.
- `src/TerminalScene.tsx` — the animated terminal component (from
  `calesthio/openmontage` `remotion-composer`, with `import React` prepended).

## Narration (ElevenLabs)

The render is silent; the voice-over is generated separately and muxed on top.
Each segment's delay is an absolute video-time cue locked to the beats in
`DemoVideo.tsx` / `SimulatorScene.tsx` (0s problem · 9.5s simulator · 47.5s
terminal).

```bash
export ELEVENLABS_API_KEY=sk_...
python3 narrate.py            # writes /tmp/el_audio9/seg1..seg9.mp3 + prints offsets
# assemble:  ffmpeg -i seg1.mp3 ... -i seg9.mp3 -filter_complex "adelay/amix/apad" -t 80.3 narration.wav
# mux:       ffmpeg -i demo.mp4 -i narration.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest out.mp4
```

The API key is never committed; it is read from the environment only. The
narration uses the **Eleven v3** model (recommended for video narration), Natural
stability, and speech-normalized text ("M-C-P" spelled out, ellipses for pacing).

## Note

The content is scripted from the deterministic engine output (not live LLM calls),
so rendering needs no network or API key. The narration is an ElevenLabs "Adam"
voice over nine beats: a problem-first opening, four simulator beats (the voice
experience, the tool calls, the rubric, the disclaimer), and four terminal beats
(protocol view, tools + scenarios, safety boundary, closing line).
