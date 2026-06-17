"""Renderer adapter skeleton for the experimental Rust canvas backend."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from p5.assets.image import Image
from p5.core.color import Color
from p5.core.state import StyleState
from p5.core.transform import Matrix2D
from p5.exceptions import BackendCapabilityError


class CanvasRenderer:
    """Renderer protocol adapter for ``p5.rust._canvas``.

    The foundation bridge only proves extension discovery and backend selection.
    Rendering methods intentionally fail until Rust canvas operations are exposed.
    """

    def __init__(self, canvas_module: object | None = None) -> None:
        self._canvas_module = canvas_module
        self.width = 0
        self.height = 0
        self.physical_width = 0
        self.physical_height = 0
        self.pixel_density = 1.0

    def resize(self, width: int, height: int, pixel_density: float = 1.0) -> None:
        self._raise_unimplemented("canvas allocation and resize")

    def begin_frame(self) -> None:
        self._raise_unimplemented("frame setup")

    def end_frame(self) -> None:
        self._raise_unimplemented("frame finalization")

    def background(self, color: Color) -> None:
        self._raise_unimplemented("background drawing")

    def clear(self) -> None:
        self._raise_unimplemented("canvas clearing")

    def point(self, x: float, y: float, style: StyleState, transform: Matrix2D) -> None:
        self._raise_unimplemented("point drawing")

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        style: StyleState,
        transform: Matrix2D,
    ) -> None:
        self._raise_unimplemented("line drawing")

    def polygon(
        self,
        points: list[tuple[float, float]],
        style: StyleState,
        transform: Matrix2D,
        *,
        close: bool = True,
    ) -> None:
        self._raise_unimplemented("polygon drawing")

    def ellipse(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        style: StyleState,
        transform: Matrix2D,
    ) -> None:
        self._raise_unimplemented("ellipse drawing")

    def arc(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        start: float,
        stop: float,
        mode: str,
        style: StyleState,
        transform: Matrix2D,
    ) -> None:
        self._raise_unimplemented("arc drawing")

    def draw_image(
        self,
        image: Image,
        dx: float,
        dy: float,
        dw: float,
        dh: float,
        style: StyleState,
        transform: Matrix2D,
        *,
        source: tuple[int, int, int, int] | None = None,
    ) -> None:
        self._raise_unimplemented("image drawing")

    def text(
        self,
        value: str,
        x: float,
        y: float,
        style: StyleState,
        transform: Matrix2D,
    ) -> None:
        self._raise_unimplemented("text drawing")

    def text_width(self, value: str, style: StyleState) -> float:
        self._raise_unimplemented("text metrics")

    def text_ascent(self, style: StyleState) -> float:
        self._raise_unimplemented("text metrics")

    def text_descent(self, style: StyleState) -> float:
        self._raise_unimplemented("text metrics")

    def load_pixels(self) -> list[int]:
        self._raise_unimplemented("pixel readback")

    def update_pixels(self, pixels: Sequence[int]) -> None:
        self._raise_unimplemented("pixel upload")

    def blend_region(
        self,
        source_image: object | None,
        source: tuple[int, int, int, int],
        destination: tuple[int, int, int, int],
        mode: str,
    ) -> None:
        self._raise_unimplemented("region blending")

    def save(self, path: str | Path) -> None:
        self._raise_unimplemented("canvas export")

    def _raise_unimplemented(self, operation: str) -> NoReturn:
        raise BackendCapabilityError(
            "The experimental 'canvas' backend found p5.rust._canvas, but "
            f"{operation} is not implemented yet. Use backend='pyglet' or "
            "backend='headless' for rendering."
        )
