# mobile-screen-video-reader

Extract frames from smartphone screen recordings and prepare them for AI review in
Claude/Codex workflows.

![Status](https://img.shields.io/badge/status-oss-green)

## Features

- Extract still frames from a video with fixed-frame (`every`) or fixed-interval
  (`interval`) sampling
- Extract scene-change frames (`scene`) for rough activity summary
- Generate:
  - `manifest.json` (metadata + extracted frame list)
  - `frames.jsonl` (line-based frame index)
  - `report.md` (human-readable summary)
- Optional OpenAI transcription
- Designed to be used as a local skill utility and copy/paste friendly

## Requirements

- Python 3.10+
- FFmpeg and ffprobe
- Optional: `openai` package and `OPENAI_API_KEY` for transcription

## Install and use (local repo)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

mobile-screen-video-reader \
  /path/to/screen-recording.mp4 \
  --output-dir ./output \
  --mode interval \
  --interval 2
```

### Available options

```text
usage: mobile-screen-video-reader [video] [--output-dir OUTPUT_DIR]
  [--mode {every,interval,scene}] [--fps FPS] [--interval INTERVAL]
  [--scene-threshold SCENE_THRESHOLD] [--max-width MAX_WIDTH]
  [--max-frames MAX_FRAMES] [--image-format {jpg,png}] [--quality QUALITY]
  [--transcribe] [--keep-audio] [--model MODEL] [--lang LANG]
```

## Example output

```text
output/
  mobile-app-demo-20260405-093000/
    frames/
      frame_000001.jpg
      frame_000002.jpg
      ...
    manifest.json
    frames.jsonl
    report.md
    transcript.json (if --transcribe enabled and key present)
```

## Install as a Codex skill

- Copy this folder to `~/.codex/skills/mobile-screen-video-reader`.
- Run `python3 scripts/mobile_screen_video_reader.py <video path> ...` in that
  folder when needed.

`SKILL.md` and `agents/openai.yaml` are included for skill metadata.

## OpenAI Transcription

Transcription is disabled unless `--transcribe` is enabled.

```bash
export OPENAI_API_KEY=...
mobile-screen-video-reader screen-recording.mp4 --transcribe --keep-audio
```

## License

MIT
