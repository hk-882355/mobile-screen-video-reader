from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
import unittest


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
        self.assertIn("# App Imitation Prompt", prompt)
        self.assertIn("Source video: `sample.mp4`", prompt)
        self.assertIn("flow.jsonl", prompt)
        self.assertIn("timeline", prompt.lower())

if __name__ == "__main__":
    unittest.main()
