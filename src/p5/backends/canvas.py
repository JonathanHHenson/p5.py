"""Experimental Rust-powered canvas backend skeleton."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from p5 import constants as c
from p5.backends.base import BackendCapabilities
from p5.backends.canvas_renderer import CanvasRenderer
from p5.exceptions import BackendCapabilityError
from p5.rust.canvas import canvas_health_check, require_canvas_extension

if TYPE_CHECKING:
    from p5.sketch import Sketch


class CanvasBackend:
    """Opt-in backend adapter for the future ``p5_canvas`` Rust runtime."""

    name = c.CANVAS
    capabilities = BackendCapabilities(
        interactive=False,
        headless=False,
        text=False,
        images=False,
        pixels=False,
        pixel_readback=False,
        pixel_update=False,
        canvas_export=False,
        mouse=False,
        keyboard=False,
        touch=False,
        paths=False,
        transforms=False,
        blend_modes=frozenset(),
        three_d=False,
        shaders=False,
        sound=False,
    )

    def __init__(self) -> None:
        self._canvas_module = require_canvas_extension()
        self.capabilities = type(self).capabilities
        self.renderer = CanvasRenderer(self._canvas_module)
        self._running = False

    def health_check(self) -> str:
        """Return the underlying Rust canvas extension health check."""

        return canvas_health_check()

    def create_canvas(
        self,
        width: int,
        height: int,
        pixel_density: float | None = None,
        *,
        renderer: str = c.P2D,
    ) -> None:
        self._raise_unimplemented("canvas creation")

    def resize_canvas(
        self,
        width: int,
        height: int,
        pixel_density: float | None = None,
        *,
        renderer: str = c.P2D,
    ) -> None:
        self._raise_unimplemented("canvas resizing")

    def display_density(self) -> float:
        self._raise_unimplemented("display-density reporting")

    def run(self, sketch: Sketch, *, max_frames: int | None = None) -> None:
        self._raise_unimplemented("frame scheduling")

    def stop(self) -> None:
        self._running = False

    def present(self) -> None:
        self._raise_unimplemented("frame presentation")

    def _raise_unimplemented(self, operation: str) -> NoReturn:
        raise BackendCapabilityError(
            "The experimental 'canvas' backend found p5.rust._canvas, but "
            f"{operation} is not implemented yet. Use backend='pyglet' or "
            "backend='headless' until p5_canvas rendering/runtime support lands."
        )
