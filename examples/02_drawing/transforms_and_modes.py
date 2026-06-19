"""Push/pop transforms, angle modes, shape modes, and matrix resets."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import p5
from examples.common import example_parser, save_once

OUTPUT = Path("examples/output/02_drawing/transforms_and_modes.png")
ARGS = example_parser(__doc__ or "", OUTPUT).parse_args()


@p5.setup
def setup() -> None:
    p5.create_canvas(720, 420)
    p5.angle_mode(p5.DEGREES)
    p5.rect_mode(p5.CENTER)
    p5.ellipse_mode(p5.CENTER)


@p5.draw
def draw() -> None:
    p5.background(236, 239, 232)

    with p5.style(stroke=(34, 36, 42), stroke_weight=2):
        for row in range(3):
            for col in range(6):
                with p5.transform(
                    translate=(80 + col * 112, 85 + row * 112),
                    rotate=p5.current.frame_count * 2 + row * 18 + col * 9,
                    scale=(1 + row * 0.12, 1 + col * 0.02),
                ):
                    p5.fill(230 - row * 34, 105 + col * 18, 88 + row * 44, 210)
                    p5.rect(0, 0, 54, 54)
                    p5.no_fill()
                    p5.circle(0, 0, 76)

    with p5.style(fill=(24, 28, 38), stroke=None):
        p5.text_size(15)
        p5.text(
            "Each tile uses isolated transform() contexts; text is drawn outside them.",
            24,
            394,
        )

    save_once(ARGS, p5.current.frame_count, p5.save_canvas)


if __name__ == "__main__":
    p5.run(headless=ARGS.headless, max_frames=ARGS.frames)
