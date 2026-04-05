---
name: "mobile-screen-video-reader"
description: "Convert smartphone screen-recording videos into keyframes and optionally transcribe audio so Claude/Codex can review UI behavior from path-based video assets."
---

# Mobile Screen Video Reader

## What this skill does

- Convert one video file to still frames.
- Keep outputs stable and easy for AI context:
  - `manifest.json`
  - `frames.jsonl`
  - `report.md`
  - `transcript.json` (only when transcription is enabled)

## Triggering

Use this skill when the user provides a screen recording path and wants a quick
UI review package for AI, instead of manually inspecting a long video.

## Default behavior

1. Build a timestamped output folder under the configured output directory.
2. Extract one frame per second by default (`--mode every --fps 1`).
3. Emit a manifest with frame paths.
4. If transcription is requested, extract audio and call OpenAI Audio API if
   `OPENAI_API_KEY` is available.

## Workflow

```bash
python3 scripts/mobile_screen_video_reader.py \
  /path/to/recording.mp4 \
  --output-dir output \
  --mode interval \
  --interval 2 \
  --transcribe
```

## Error handling

- Missing `ffmpeg`/`ffprobe`: fail early with a clear message.
- Missing `OPENAI_API_KEY` or `openai` package: skip transcription and continue
  with frame extraction.

## Notes for long videos

- If the run is too large, use `--max-frames` to cap output size.
- Prefer `--mode interval --interval 2` for app flows where one frame every few
  seconds is enough.
