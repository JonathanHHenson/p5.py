"""Mouse, keyboard, movement deltas, buttons, and touch state access."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import p5
from examples.common import example_parser, save_once

OUTPUT = Path("examples/output/05_interaction/input_state.png")
ARGS = example_parser(__doc__ or "", OUTPUT).parse_args()


@p5.setup
def setup() -> None:
    p5.create_canvas(620, 360)
    p5.frame_rate(60)


@p5.draw
def draw() -> None:
    p5.background(238, 241, 236)
    position = p5.mouse.position
    x = position.x or 310
    y = position.y or 180

    p5.no_stroke()
    p5.fill(34, 118, 210, 210 if p5.mouse.is_pressed else 130)
    p5.circle(x, y, 54)
    p5.stroke(32, 36, 44)
    p5.line(p5.mouse.previous_position, position)

    p5.no_stroke()
    p5.fill(30, 34, 44)
    p5.text_size(15)
    rows = [
        f"mouse: ({p5.mouse.x:.1f}, {p5.mouse.y:.1f})",
        f"previous: ({p5.mouse.previous_x:.1f}, {p5.mouse.previous_y:.1f})",
        f"moved: ({p5.mouse.moved_x:.1f}, {p5.mouse.moved_y:.1f})",
        f"mouse pressed: {p5.mouse.is_pressed}  button: {p5.mouse.button}",
        f"key pressed: {p5.keyboard.is_pressed}  key: {p5.keyboard.key}  code: {p5.keyboard.code}",
        f"left arrow down: {p5.keyboard.is_down(p5.LEFT_ARROW)}",
        f"touch count: {len(p5.touches())}",
    ]
    for i, row in enumerate(rows):
        p5.text(row, 28, 38 + i * 28)

    save_once(ARGS, p5.current.frame_count, p5.save_canvas)


if __name__ == "__main__":
    p5.run(headless=ARGS.headless, max_frames=ARGS.frames)
