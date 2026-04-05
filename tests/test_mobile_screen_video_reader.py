from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
import unittest
import tempfile


def load_script_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "mobile_screen_video_reader.py"
    spec = importlib.util.spec_from_file_location("msvr", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load script module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


module = load_script_module()


class TestMobileScreenVideoReader(unittest.TestCase):
    def test_sanitize_slug(self) -> None:
        self.assertEqual(module.sanitize_slug("My Recording 2026.mp4"), "my-recording-2026.mp4")
        self.assertEqual(module.sanitize_slug("Hello@#World"), "hello-world")

    def test_to_fraction(self) -> None:
        self.assertEqual(module.to_fraction("30/1"), 30.0)
        self.assertEqual(module.to_fraction("30000/1001"), float(30000 / 1001))
        self.assertEqual(module.to_fraction("0.5"), 0.5)

    def test_build_video_filter_scene_mode(self) -> None:
        args = type(
            "Args",
            (),
            {
                "mode": "scene",
                "fps": 1.0,
                "interval": 2.0,
                "scene_threshold": 0.05,
                "diff_threshold": 0.06,
                "diff_interval": 0.5,
                "max_width": 768,
            },
        )()
        vf = module.build_video_filter(args)
        self.assertIn("select='gt(scene,0.05)'", vf)
        self.assertIn("scale=min(768,iw):-2", vf)

    def test_build_video_filter_diff_mode(self) -> None:
        args = type(
            "Args",
            (),
            {
                "mode": "diff",
                "fps": 1.0,
                "interval": 2.0,
                "scene_threshold": 0.04,
                "diff_threshold": 0.08,
                "diff_interval": 0.75,
                "max_width": 768,
            },
        )()
        vf = module.build_video_filter(args)
        self.assertIn("fps=1/0.75", vf)
        self.assertIn("select='gt(scene,0.08)'", vf)

    def test_build_video_filter_mimic_mode(self) -> None:
        args = type(
            "Args",
            (),
            {
                "mode": "mimic",
                "fps": 1.0,
                "interval": 2.0,
                "scene_threshold": 0.04,
                "diff_threshold": 0.09,
                "diff_interval": 1.0,
                "max_width": 768,
            },
        )()
        vf = module.build_video_filter(args)
        self.assertIn("fps=1/1.0", vf)
        self.assertIn("select='gt(scene,0.09)'", vf)

    def test_build_flow_rows(self) -> None:
        frame_rows = [
            {"index": 1, "frame": "frame_000001.jpg", "timestamp_sec": 0.0},
            {"index": 2, "frame": "frame_000002.jpg", "timestamp_sec": 1.2},
            {"index": 3, "frame": "frame_000003.jpg", "timestamp_sec": 1.9},
        ]
        flow = module.build_flow_rows(frame_rows)
        self.assertEqual(flow[0]["step"], 1)
        self.assertNotIn("delta_sec", flow[0])
        self.assertEqual(flow[1]["delta_sec"], 1.2)
        self.assertEqual(flow[2]["delta_sec"], 0.7)

    def test_build_mimic_prompt(self) -> None:
        prompt = module.build_mimic_prompt(
            video_path=Path("/tmp/sample.mp4"),
            flow_rows=[
                {"step": 1, "image": "frame_000001.jpg", "timestamp_sec": 0.0},
                {"step": 2, "image": "frame_000002.jpg", "timestamp_sec": 1.5},
            ],
        )
        self.assertIn("# Screen Sequence Review Prompt", prompt)
        self.assertIn("Source video: `sample.mp4`", prompt)
        self.assertIn("flow.jsonl", prompt)
        self.assertIn("timeline", prompt.lower())

    def test_resolve_review_prompt_name_default(self) -> None:
        args = type(
            "Args",
            (),
            {
                "review_prompt": None,
                "mimic_prompt": None,
            },
        )()
        self.assertEqual(module.resolve_review_prompt_name(args), "codex_review_prompt.md")

    def test_resolve_review_prompt_name_review_only(self) -> None:
        args = type(
            "Args",
            (),
            {
                "review_prompt": "review_timeline.md",
                "mimic_prompt": None,
            },
        )()
        self.assertEqual(module.resolve_review_prompt_name(args), "review_timeline.md")

    def test_resolve_review_prompt_name_legacy_only(self) -> None:
        args = type(
            "Args",
            (),
            {
                "review_prompt": None,
                "mimic_prompt": "legacy_timeline.md",
            },
        )()
        self.assertEqual(module.resolve_review_prompt_name(args), "legacy_timeline.md")

    def test_resolve_review_prompt_name_conflict(self) -> None:
        args = type(
            "Args",
            (),
            {
                "review_prompt": "a.md",
                "mimic_prompt": "b.md",
            },
        )()
        with self.assertRaises(ValueError):
            module.resolve_review_prompt_name(args)

    def test_resolve_mimic_prompt_path(self) -> None:
        output_dir = Path("/tmp/out")
        out = module.resolve_mimic_prompt_path(output_dir=output_dir, prompt_name="ui_replay_prompt.md")
        self.assertEqual(str(out), str(output_dir / "ui_replay_prompt.md"))

    def test_resolve_mimic_prompt_path_rejects_parent(self) -> None:
        output_dir = Path("/tmp/out")
        with self.assertRaises(ValueError):
            module.resolve_mimic_prompt_path(output_dir=output_dir, prompt_name="../evil.md")

    def test_write_artifacts_sequence_review_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "run"
            output_dir.mkdir(parents=True, exist_ok=True)
            frame_dir = output_dir / "frames"
            frame_dir.mkdir()
            frame1 = frame_dir / "frame_000001.jpg"
            frame2 = frame_dir / "frame_000002.jpg"
            frame1.write_text("f1")
            frame2.write_text("f2")

            args = type(
                "Args",
                (),
                {
                    "mode": "mimic",
                    "review_prompt": "custom_review.md",
                    "mimic_prompt": None,
                    "image_format": "jpg",
                    "fps": 1.0,
                    "interval": 2.0,
                    "scene_threshold": 0.04,
                    "diff_threshold": 0.06,
                    "diff_interval": 0.5,
                    "max_width": 768,
                    "max_frames": 0,
                    "quality": 2,
                    "transcribe": False,
                    "model": "gpt-4o-mini-transcribe",
                    "lang": None,
                },
            )()

            manifest = module.write_artifacts(
                output_dir=output_dir,
                video_path=Path("/tmp/sample.mp4"),
                metadata={"duration": 10.0, "width": 1080, "height": 1920, "fps": 30.0},
                frames=[frame1, frame2],
                args=args,
                timestamps=[0.0, 1.0],
                transcript=None,
            )

            self.assertIn("sequence_review", manifest)
            self.assertIn("mimic", manifest)
            self.assertEqual(manifest["sequence_review"], manifest["mimic"])
            self.assertEqual(manifest["sequence_review"]["prompt_path"], "custom_review.md")

    def test_validate_video_metadata(self) -> None:
        metadata = {"duration": 90.0, "width": 1080, "height": 1920}
        args = type(
            "Args",
            (),
            {
                "max_duration": 120.0,
                "min_duration": 10.0,
            },
        )()
        warnings = module.validate_video_metadata(metadata=metadata, args=args)
        self.assertEqual(warnings, [])

    def test_validate_video_metadata_rejects_too_long(self) -> None:
        metadata = {"duration": 600.0, "width": 1080, "height": 1920}
        args = type(
            "Args",
            (),
            {
                "max_duration": 120.0,
                "min_duration": 0.0,
            },
        )()
        with self.assertRaises(RuntimeError):
            module.validate_video_metadata(metadata=metadata, args=args)

if __name__ == "__main__":
    unittest.main()
