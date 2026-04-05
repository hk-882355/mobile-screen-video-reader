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
  - `flow.jsonl` (mimic mode)
  - `codex_mimic_prompt.md` (mimic mode)
  - `transcript.json` (only when transcription is enabled)

## Triggering

Use this skill when the user provides a screen recording path and wants a quick
UI review / UI imitation package for AI, instead of manually inspecting a long
video.

## Default behavior

1. Build a timestamped output folder under the configured output directory.
2. Extract by selected mode:
   - `every`: every second by default (`--mode every --fps 1`)
   - `interval`: fixed interval (`--mode interval --interval 2`)
   - `scene`: scene transitions (`--mode scene`)
   - `diff`: UI-diff focused transitions (`--mode diff --diff-threshold ...`)
   - `mimic`: preset for app imitation/replay (`--mode mimic`)
3. Emit a manifest with frame paths.
4. In `--mode diff`, tune `--diff-threshold` (sensitivity) and
   `--diff-interval` (sampling interval before diff detection).
5. In `--mode mimic`, automatically add `flow.jsonl` + `codex_mimic_prompt.md` for quick imitation workflow.
6. If transcription is requested, extract audio and call OpenAI Audio API if
   `OPENAI_API_KEY` is available.
7. Optional: set `--max-duration` to guard against accidentally long recordings.
8. Optional: set `--mimic-prompt` to customize the generated prompt filename.

## Workflow

```bash
python3 scripts/mobile_screen_video_reader.py \
  /path/to/recording.mp4 \
  --output-dir output \
  --mode diff \
  --diff-interval 0.5 \
  --diff-threshold 0.06
```

## Error handling

- Missing `ffmpeg`/`ffprobe`: fail early with a clear message.
- Missing `OPENAI_API_KEY` or `openai` package: skip transcription and continue
  with frame extraction.

## Notes for long videos

- If the run is too large, use `--max-frames` to cap output size.
- Prefer `--mode interval --interval 2` for app flows where one frame every few
  seconds is enough.
- Prefer `--mode mimic` when the goal is to recreate a UI flow and preserve
  transition order.
- Guard against too-long videos with `--max-duration` when batch ingesting.
