# mobile-screen-video-reader

Extract frames from smartphone screen recordings and prepare them for AI review in
Claude/Codex workflows.

![Status](https://img.shields.io/badge/status-oss-green)

## Features

- Extract still frames from a video with fixed-frame (`every`) or fixed-interval
  (`interval`) sampling
- Extract scene-change frames (`scene`) for rough activity summary
- Add UI-diff mode (`diff`) to focus on likely UI transition points
- Add sequence-focused mode (`mimic`) for ordered, review-friendly extraction
- In `mimic` mode, also export:
  - `flow.jsonl` (ordered timeline for quick sequence reading)
  - `codex_review_prompt.md` (ready-to-use review prompt template)
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

## Install and use

### Install from PyPI

```bash
# (PyPI 公開後に有効)
pip install mobile-screen-video-reader
```

### Install from local repo

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

## Release flow

GitHub Actions publishes package artifacts automatically when a `v*` tag is pushed:

- `python -m build` generates distribution files
- `twine check` validates artifacts
- publishes to PyPI via trusted publishing
- attaches `dist/*` artifacts to a GitHub release

If you need manual publish, use:

```bash
PYPI_API_TOKEN=... # PyPI API token
python -m pip install -q twine
python -m twine upload -u __token__ -p "$PYPI_API_TOKEN" dist/*
```

### Trusted publishing setup

The default `Release` workflow uses [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/) for
`pypa/gh-action-pypi-publish@release/v1`.

If publishing fails on `trusted-publisher` errors, configure a trusted publisher in PyPI first:

- Account: `hk-882355`
- Repository: `mobile-screen-video-reader`
- Workflow file: `.github/workflows/release.yml`
- Environment: not required (the current job does not use one)

Then rerun:

```bash
gh workflow run Release --ref main --field publish=true
```

For manual dispatch publishing, pass `publish=true` explicitly.

or push a new `v*` tag to trigger the same path automatically.

### Available options

```text
usage: mobile-screen-video-reader [video] [--output-dir OUTPUT_DIR]
  [--mode {every,interval,scene,diff,mimic}] [--fps FPS] [--interval INTERVAL]
  [--scene-threshold SCENE_THRESHOLD] [--diff-threshold DIFF_THRESHOLD]
  [--diff-interval DIFF_INTERVAL] [--max-duration MAX_DURATION]
  [--min-duration MIN_DURATION] [--max-width MAX_WIDTH]
  [--max-frames MAX_FRAMES] [--image-format {jpg,png}] [--quality QUALITY]
  [--transcribe] [--keep-audio] [--model MODEL] [--lang LANG]
  [--review-prompt REVIEW_PROMPT] [--mimic-prompt MIMIC_PROMPT]
```

### Sequence reading preset

```bash
mobile-screen-video-reader \
  /path/to/screen-recording.mp4 \
  --output-dir ./output \
  --mode mimic
```

`mimic` uses the `diff` pipeline with preset-friendly defaults for ordered flow review.

### Recommended for sequence review

```bash
OUT_DIR=./output
video=/path/to/screen-recording.mp4
mobile-screen-video-reader \
  "$video" \
  --output-dir "$OUT_DIR" \
  --mode mimic \
  --max-duration 600 \
  --review-prompt review_timeline_prompt.md

echo "この画面録画のフレームとタイムラインをAIに渡して要約してください"
```

`--mimic-prompt` is kept for backward compatibility and maps to
`--review-prompt`.

Suggested next step:
- Attach generated files under `${OUT_DIR}/<run-folder>/` into Claude/Codex context
- Start with `${OUT_DIR}/.../review_timeline_prompt.md`, then reference `frames/` and `flow.jsonl`

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
    flow.jsonl (mimic mode)
    codex_review_prompt.md (mimic mode)
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
