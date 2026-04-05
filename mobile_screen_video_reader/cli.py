"""Package entrypoint wrapper for the script-based implementation."""

from __future__ import annotations

import pathlib
import runpy
import sys


def main() -> int:
    script = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "mobile_screen_video_reader.py"
    namespace = runpy.run_path(str(script))
    return int(namespace["main"]())


if __name__ == "__main__":
    sys.exit(main())
