"""Package entrypoint wrapper for the packaged implementation."""

from __future__ import annotations

import sys

from mobile_screen_video_reader.app import main as app_main


def main() -> int:
    return int(app_main())


if __name__ == "__main__":
    sys.exit(main())
