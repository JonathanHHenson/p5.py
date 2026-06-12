"""Font abstraction for p5-py text APIs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import ImageFont

from p5_py.exceptions import ArgumentValidationError


@dataclass(frozen=True, slots=True)
class Font:
    path: Path | None = None
    name: str | None = None

    def pillow_font(self, size: float) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
        point_size = max(1, int(round(size)))
        if self.path is None:
            return ImageFont.load_default(point_size)
        try:
            return ImageFont.truetype(str(self.path), point_size)
        except OSError as exc:
            raise ArgumentValidationError(f"Could not load font {self.path!s}.") from exc


def load_font(path: str | Path) -> Font:
    font_path = Path(path)
    if not font_path.exists():
        raise ArgumentValidationError(f"Font file does not exist: {font_path!s}.")
    return Font(path=font_path)


DEFAULT_FONT = Font(name="default")

__all__ = ["Font", "DEFAULT_FONT", "load_font"]
