#!/usr/bin/env python3
"""Extract representative frames from a mobile screen recording video."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def run_cmd(cmd: List[str], check: bool = True, **kwargs: Any) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=True, **kwargs)


def require_command(name: str) -> None:
    if not shutil.which(name):
        raise RuntimeError(f"{name} is required but was not found. Please install FFmpeg.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract frames from a screen recording video for AI review.",
    )
    parser.add_argument("video", help="Path to input video file")
    parser.add_argument(
        "--output-dir",
        default="output/mobile-screen-video-reader",
        help="Output root folder",
    )
    parser.add_argument(
        "--mode",
        choices=("every", "interval", "scene", "diff", "mimic"),
        default="every",
        help="every: fixed fps, interval: fixed seconds, scene/diff/mimic: change-based",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=1.0,
        help="Frames per second when mode=every",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds per frame when mode=interval",
    )
    parser.add_argument(
        "--scene-threshold",
        type=float,
        default=0.04,
        help="Scene change sensitivity when mode=scene",
    )
    parser.add_argument(
        "--diff-threshold",
        type=float,
        default=0.06,
        help="UI-diff sensitivity when mode=diff/mimic (higher is less sensitive)",
    )
    parser.add_argument(
        "--diff-interval",
        type=float,
        default=0.5,
        help="Sampling interval in seconds before diff filtering. Used for mode=diff and mimic",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=0.0,
        help="Reject videos longer than this many seconds (0 means no limit)",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=0.0,
        help="Warn for videos shorter than this many seconds (0 means no warning)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=768,
        help="Maximum width for extracted frame",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Optional cap for frame count (0 means no limit)",
    )
    parser.add_argument(
        "--image-format",
        choices=("jpg", "png"),
        default="jpg",
        help="Output image format",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=2,
        help="JPEG quality q:v scale (lower means higher quality). Ignored for PNG",
    )
    parser.add_argument(
        "--transcribe",
        action="store_true",
        help="Transcribe audio with OpenAI's audio API (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep extracted audio file. By default it is removed.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini-transcribe",
        help="OpenAI transcription model",
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Optional language hint for transcription (e.g. ja)",
    )
    parser.add_argument(
        "--mimic-prompt",
        default="codex_mimic_prompt.md",
        help="Mimic mode prompt output filename (written under output folder)",
    )
    return parser.parse_args()


def to_fraction(value: str) -> float:
    if "/" in value:
        num, den = value.split("/")
        if not den or den == "0":
            return 0.0
        return float(Fraction(int(num), int(den)))
    try:
        return float(value)
    except ValueError:
        return 0.0


def ffprobe_video_metadata(path: Path) -> Dict[str, Any]:
    res = run_cmd(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-show_entries",
            "stream=codec_name,width,height,avg_frame_rate,nb_frames,duration",
            "-select_streams",
            "v:0",
            "-of",
            "json",
            str(path),
        ],
    )
    payload = json.loads(res.stdout)
    streams = payload.get("streams", [])
    info = streams[0] if streams else {}
    fmt = payload.get("format", {})
    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    fps = to_fraction(info.get("avg_frame_rate") or "0/1")
    duration = float(info.get("duration") or fmt.get("duration") or 0.0)
    nb_frames = int(info.get("nb_frames") or 0)
    codec = info.get("codec_name", "unknown")
    return {
        "codec": codec,
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "frames": nb_frames,
    }


def resolve_mimic_prompt_path(output_dir: Path, prompt_name: str) -> Path:
    prompt_path = Path(prompt_name)
    if prompt_path.is_absolute() or ".." in prompt_path.parts:
        raise ValueError("mimic prompt path must be a file name relative to the output folder")
    if not prompt_path.suffix:
        prompt_path = prompt_path.with_suffix(".md")
    return output_dir / prompt_path


def validate_video_metadata(metadata: Dict[str, Any], args: argparse.Namespace) -> List[str]:
    warnings = []
    duration = float(metadata.get("duration", 0.0))
    if duration <= 0:
        raise RuntimeError("Could not determine video duration. Please check FFmpeg input.")
    if args.max_duration and duration > args.max_duration:
        raise RuntimeError(
            f"Video is too long: {duration:.2f}s. "
            f"Use --max-duration {args.max_duration} to adjust threshold."
        )
    if args.min_duration and duration < args.min_duration:
        warnings.append(f"Short video: {duration:.2f}s. Some transitions may be missing.")

    width = int(metadata.get("width", 0))
    height = int(metadata.get("height", 0))
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Could not determine frame size from this video: {width}x{height}")
    if width < 360 or height < 360:
        warnings.append(f"Low resolution detected: {width}x{height}. Results may be noisy.")
    return warnings


def build_video_filter(args: argparse.Namespace) -> str:
    parts: List[str] = []
    max_width = max(64, int(args.max_width))
    if args.mode == "every":
        fps = max(args.fps, 0.01)
        parts.append(f"fps={fps}")
    elif args.mode == "interval":
        interval = max(args.interval, 0.1)
        parts.append(f"fps=1/{interval}")
    elif args.mode == "scene":
        th = max(0.01, min(1.0, args.scene_threshold))
        parts.append(f"select='gt(scene,{th})'")
    else:
        interval = max(0.1, args.diff_interval)
        th = max(0.01, min(1.0, args.diff_threshold))
        parts.append(f"fps=1/{interval}")
        parts.append(f"select='gt(scene,{th})'")

    parts.append(f"scale=min({max_width},iw):-2")
    return ", ".join(parts)


def timestamp_list(metadata: Dict[str, Any], mode: str, args: argparse.Namespace) -> Iterable[float]:
    duration = float(metadata.get("duration", 0.0))
    if duration <= 0:
        return ()
    if mode == "every":
        interval = 1.0 / max(args.fps, 0.01)
        count = int(duration / interval) + 1
        return [round(i * interval, 3) for i in range(count)]
    if mode == "interval":
        interval = max(args.interval, 0.1)
        count = int(duration / interval) + 1
        return [round(i * interval, 3) for i in range(count)]
    if mode in ("diff", "mimic"):
        interval = max(0.1, args.diff_interval)
        count = int(duration / interval) + 1
        return [round(i * interval, 3) for i in range(count)]
    return ()


def sanitize_slug(name: str) -> str:
    name = name.lower().replace(" ", "-")
    name = re.sub(r"[^a-z0-9._-]", "-", name)
    return re.sub(r"-+", "-", name).strip("-.")


def build_output_dir(video: Path, base: Path) -> Path:
    stem = sanitize_slug(video.stem) or "video"
    target = base / f"{stem}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def extract_frames(video_path: Path, output_dir: Path, args: argparse.Namespace) -> List[Path]:
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    out_template = frames_dir / f"frame_%06d.{args.image_format}"
    vf = build_video_filter(args)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        vf,
    ]
    if args.max_frames > 0:
        cmd += ["-frames:v", str(args.max_frames)]
    cmd += [
        "-q:v",
        str(args.quality),
        "-pix_fmt",
        "yuv420p",
        "-y",
        str(out_template),
    ]
    run_cmd(cmd)
    frames = sorted(frames_dir.glob(f"*.{args.image_format}"))
    return frames


def extract_audio(video_path: Path, output_dir: Path) -> Optional[Path]:
    audio_path = output_dir / "audio.wav"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-y",
        str(audio_path),
    ]
    run_cmd(cmd)
    return audio_path if audio_path.exists() else None


def transcribe_audio(audio_path: Path, model: str, lang: Optional[str]) -> Dict[str, Any]:
    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError("openai package is not installed; cannot transcribe") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; cannot transcribe")

    client = OpenAI(api_key=api_key)
    params = {
        "model": model,
        "file": open(audio_path, "rb"),
        "response_format": "verbose_json",
    }
    if lang:
        params["language"] = lang

    try:
        response = client.audio.transcriptions.create(**params)
    finally:
        params["file"].close()

    if hasattr(response, "model_dump"):
        return response.model_dump()
    if isinstance(response, dict):
        return response
    return dict(response)


def write_artifacts(
    output_dir: Path,
    video_path: Path,
    metadata: Dict[str, Any],
    frames: List[Path],
    args: argparse.Namespace,
    timestamps: List[float],
    transcript: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    ts_iter = iter(timestamps)
    frame_rows = []
    for index, frame in enumerate(sorted(frames), start=1):
        row = {
            "index": index,
            "file": str(frame.relative_to(output_dir)),
            "frame": frame.name,
        }
        if args.mode in ("every", "interval", "diff", "mimic"):
            row["timestamp_sec"] = next(ts_iter, None)
        frame_rows.append(row)

    manifest = {
        "version": 1,
        "created_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "video": {
            "path": str(video_path),
            "filename": video_path.name,
            "metadata": metadata,
        },
        "settings": {
            "mode": args.mode,
            "fps": args.fps,
            "interval": args.interval,
            "scene_threshold": args.scene_threshold,
            "diff_threshold": args.diff_threshold,
            "diff_interval": args.diff_interval,
            "max_width": args.max_width,
            "max_frames": args.max_frames,
            "image_format": args.image_format,
            "quality": args.quality,
            "transcribe": args.transcribe,
            "model": args.model,
            "lang": args.lang,
        },
        "frames": frame_rows,
        "transcript": {
            "path": "transcript.json",
            "status": "not_run",
        },
        "stats": {
            "frame_count": len(frame_rows),
        },
    }

    if transcript is not None:
        manifest["transcript"]["status"] = "ok"
        manifest["transcript"]["text"] = transcript.get("text", "")
        manifest["transcript"]["duration"] = transcript.get("duration")
        manifest["transcript"]["language"] = transcript.get("language")
        transcript_path = output_dir / "transcript.json"
        transcript_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        manifest["transcript"]["status"] = "skipped"

    if args.mode == "mimic":
        flow_path = output_dir / "flow.jsonl"
        flow_rows = build_flow_rows(frame_rows)
        flow_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in flow_rows),
            encoding="utf-8",
        )
        prompt_path = resolve_mimic_prompt_path(output_dir=output_dir, prompt_name=args.mimic_prompt)
        prompt_rel = str(prompt_path.relative_to(output_dir))
        manifest["mimic"] = {
            "flow_path": "flow.jsonl",
            "prompt_path": prompt_rel,
        }
        prompt_path.write_text(
            build_mimic_prompt(video_path=video_path, flow_rows=flow_rows),
            encoding="utf-8",
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    frame_rows_path = output_dir / "frames.jsonl"
    frame_rows_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in frame_rows),
        encoding="utf-8",
    )

    report = [
        "# Frame Extraction Report",
        "",
        f"- Input: `{video_path}`",
        f"- Mode: `{args.mode}`",
        f"- Frame count: `{len(frame_rows)}`",
        "",
        "## Quick loading commands",
        "",
        "```bash",
        f"jq . < {manifest_path.name}",
        "```",
        "",
    ]
    if frame_rows:
        report.extend([
            "## First few frames",
            "",
            "| index | file | timestamp_sec |",
            "| - | - | - |",
        ])
        for row in frame_rows[:10]:
            ts = "" if row.get("timestamp_sec") is None else row["timestamp_sec"]
            report.append(f"| {row['index']} | {row['frame']} | {ts} |")

    if transcript:
        report.append("")
        report.append("## Transcript")
        report.append("")
        report.append("```")
        report.append(transcript.get("text", ""))
        report.append("```")

    (output_dir / "report.md").write_text("\n".join(report), encoding="utf-8")

    return manifest


def build_flow_rows(frame_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flow: List[Dict[str, Any]] = []
    prev_ts: Optional[float] = None
    for row in frame_rows:
        ts = row.get("timestamp_sec")
        item: Dict[str, Any] = {
            "step": row["index"],
            "image": f"frames/{row['frame']}",
            "timestamp_sec": ts,
        }
        if prev_ts is not None and ts is not None:
            item["delta_sec"] = round(ts - prev_ts, 3)
        flow.append(item)
        if ts is not None:
            prev_ts = ts
    return flow


def build_mimic_prompt(video_path: Path, flow_rows: List[Dict[str, Any]]) -> str:
    lines = [
        "# App Imitation Prompt",
        "",
        f"Source video: `{video_path.name}`",
        "",
        "Goal:",
        "- Reconstruct the app flow as close as possible from the attached frame sequence.",
        "",
        "Instructions:",
        "- Start from the first frame and process rows in order.",
        "- For each frame, describe visible components, navigation transitions, and likely user actions.",
        "- Infer state transitions, validation states, and edge cases where visible.",
        "- Propose a minimal implementation plan and a follow-up implementation sketch in the target stack.",
        "",
        "Attached files:",
        "- `manifest.json`",
        "- `flow.jsonl`",
        "- `frames/frame_*.jpg` (or `png` depending on mode)",
        "",
        "Timeline:",
    ]
    for row in flow_rows[:80]:
        ts = "" if row.get("timestamp_sec") is None else f'{row["timestamp_sec"]}s'
        lines.append(f"- step={row['step']} image={row['image']} t={ts}")

    if len(flow_rows) > 80:
        lines.append(f"... ({len(flow_rows) - 80} more steps omitted)")
    lines.append("")
    lines.append("If uncertain, please state assumptions explicitly and produce the UI map first, then implementation details.")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    require_command("ffmpeg")
    require_command("ffprobe")

    video_path = Path(args.video).expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Input video not found: {video_path}")

    output_root = Path(args.output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    output_dir = build_output_dir(video_path, output_root)
    metadata = ffprobe_video_metadata(video_path)
    for warn in validate_video_metadata(metadata, args):
        print(f"warning: {warn}")

    frames = extract_frames(video_path, output_dir, args)
    timestamps = list(timestamp_list(metadata, args.mode, args)) if args.mode in ("every", "interval", "diff", "mimic") else []

    transcript = None
    audio_path = None
    if args.transcribe:
        try:
            audio_path = extract_audio(video_path, output_dir)
        except Exception as error:
            print(f"Audio extraction skipped: {error}")
            audio_path = None
        if audio_path:
            try:
                transcript = transcribe_audio(audio_path, args.model, args.lang)
            except Exception as error:
                print(f"Transcription skipped: {error}")
                transcript = None

    manifest = write_artifacts(
        output_dir=output_dir,
        video_path=video_path,
        metadata=metadata,
        frames=frames,
        args=args,
        timestamps=timestamps,
        transcript=transcript,
    )

    if audio_path and not args.keep_audio:
        audio_path.unlink(missing_ok=True)

    print(f"Wrote: {output_dir / 'manifest.json'}")
    print(f"Frames: {manifest['stats']['frame_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
