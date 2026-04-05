#!/usr/bin/env python3
"""Compatibility entry point script for local execution.

The actual implementation now lives in the package module so that `mobile-screen-video-reader`
can run correctly when installed from a wheel.
"""

from mobile_screen_video_reader.app import main


if __name__ == "__main__":
    raise SystemExit(main())

