"""File-backed video playback demo for the staged native media API.

Headless/export placeholder:
    uv run python examples/video_playback.py --backend headless --frames 1

Interactive with a local video file:
    uv run python examples/video_playback.py --backend pyglet --video /path/to/movie.mp4

Notes:
    - Requires the optional media extra: `uv add --optional media opencv-python-headless`
    - Audio tracks are intentionally ignored in this first milestone
    - Frames advance when `Video.read()` is called while the video is playing
"""

from __future__ import annotations

import argparse
from pathlib import Path

import p5
from p5.assets.media import Video
from p5.exceptions import ArgumentValidationError, BackendCapabilityError

OUTPUT = Path("examples/output/video_playback.png")
VIDEO: Video | None = None
EXPORT_CANVAS = False
STARTUP_MESSAGE = "Pass --video /path/to/file to play a local video."
VIDEO_PATH: Path | None = None


def setup() -> None:
    global VIDEO, STARTUP_MESSAGE

    p5.create_canvas(720, 480)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if VIDEO_PATH is None:
        return

    try:
        VIDEO = p5.create_video(VIDEO_PATH)
        VIDEO.looping(True)
        VIDEO.seek(0.0)
        VIDEO.play()
        STARTUP_MESSAGE = f"Playing {VIDEO.path.name}"
    except (ArgumentValidationError, BackendCapabilityError) as exc:
        VIDEO = None
        STARTUP_MESSAGE = str(exc)


def draw_status() -> None:
    p5.fill(245)
    p5.text_size(18)
    p5.text("create_video() demo", 28, 40)
    p5.text_size(13)
    p5.text(STARTUP_MESSAGE, 28, 72)
    p5.text("This example needs a user-supplied local video file.", 28, 96)
    p5.text("Decoded frames are returned as p5 Image values and drawn with image(...).", 28, 118)


def draw() -> None:
    p5.background(14, 16, 28)

    video = VIDEO
    frame = video.read() if video is not None else None
    if frame is not None and video is not None:
        p5.image(frame, 0, 0, p5.width(), p5.height())
        p5.fill(255)
        p5.text_size(13)
        fps = video.fps
        duration = video.duration
        stats = f"{video.width}x{video.height}"
        if fps is not None:
            stats += f"  {fps:.1f} fps"
        if duration is not None:
            stats += f"  {duration:.1f}s"
        p5.text(stats, 16, p5.height() - 18)
    else:
        draw_status()

    if EXPORT_CANVAS and p5.frame_count() == 0:
        p5.save_canvas(str(OUTPUT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=p5.HEADLESS, choices=p5.available_backends())
    parser.add_argument("--frames", type=int, default=1)
    parser.add_argument("--video", type=Path, default=None, help="Path to a local video file.")
    args = parser.parse_args()

    global EXPORT_CANVAS, VIDEO_PATH
    EXPORT_CANVAS = args.backend in {p5.HEADLESS, p5.PILLOW, p5.PYGLET}
    VIDEO_PATH = args.video
    p5.run(setup=setup, draw=draw, backend=args.backend, max_frames=args.frames)

    if VIDEO is not None:
        VIDEO.close()


if __name__ == "__main__":
    main()
