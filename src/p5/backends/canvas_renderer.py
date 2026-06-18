"""Renderer adapter for the experimental Rust canvas backend."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from math import ceil, floor
from pathlib import Path
from typing import Any

from p5 import constants as c
from p5.assets.image import Image
from p5.core.color import Color
from p5.core.state import StyleState
from p5.core.transform import Matrix2D
from p5.exceptions import ArgumentValidationError, BackendCapabilityError


def _color_payload(color: Color | None) -> tuple[int, int, int, int] | None:
    return None if color is None else color.to_tuple()


def _style_payload(style: StyleState) -> dict[str, object]:
    return {
        "fill": _color_payload(style.fill_color),
        "stroke": _color_payload(style.stroke_color),
        "stroke_weight": float(style.stroke_weight),
        "blend_mode": style.blend_mode,
        "erasing": style.erasing,
        "image_sampling": style.image_sampling,
    }


def _matrix_payload(transform: Matrix2D) -> tuple[float, float, float, float, float, float]:
    return (transform.a, transform.b, transform.c, transform.d, transform.e, transform.f)


_AFFINE_EPSILON = 1e-12


class CanvasRenderer:
    """Renderer protocol adapter for ``p5.rust._canvas``.

    The adapter keeps Python-facing renderer attributes mirrored from the Rust
    canvas and translates p5-py state objects into primitive bridge payloads.
    """

    def __init__(self, canvas_module: object | None = None) -> None:
        self._canvas_module = canvas_module
        self._canvas: Any | None = None
        self.width = 0
        self.height = 0
        self.physical_width = 0
        self.physical_height = 0
        self.pixel_density = 1.0
        self._image_cache_versions: dict[int, int] = {}
        self._text_image_cache: dict[
            tuple[str, str | None, str | None, int, tuple[int, int, int, int]],
            tuple[Image, tuple[int, int, int, int]],
        ] = {}

    def resize(
        self,
        width: int,
        height: int,
        pixel_density: float = 1.0,
        *,
        mode: str = c.HEADLESS,
    ) -> None:
        canvas_type = self._canvas_type()
        try:
            if self._canvas is None:
                self._canvas = canvas_type(width, height, pixel_density, mode, c.P2D)
            else:
                self._canvas.resize(width, height, pixel_density, c.P2D)
            self._sync_dimensions()
        except ValueError as exc:
            raise ArgumentValidationError(str(exc)) from exc

    def display_density(self) -> float:
        if self._canvas is None:
            return 1.0
        return float(self._call("display-density reporting", self._canvas.display_density))

    def begin_frame(self) -> None:
        self._require_canvas().begin_frame()

    def end_frame(self) -> None:
        self._require_canvas().end_frame()

    def present(self) -> None:
        self._require_canvas().present()

    def close(self) -> None:
        if self._canvas is not None:
            self._canvas.close()

    def runtime_canvas(self) -> Any:
        """Return the underlying Rust canvas/runtime object for backend event-loop calls."""

        return self._require_canvas()

    def background(self, color: Color) -> None:
        self._call("background drawing", self._require_canvas().background, color.to_tuple())

    def clear(self) -> None:
        self._call("canvas clearing", self._require_canvas().clear)

    def point(self, x: float, y: float, style: StyleState, transform: Matrix2D) -> None:
        self._call(
            "point drawing",
            self._require_canvas().point,
            x,
            y,
            _style_payload(style),
            _matrix_payload(transform),
        )

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        style: StyleState,
        transform: Matrix2D,
    ) -> None:
        self._call(
            "line drawing",
            self._require_canvas().line,
            x1,
            y1,
            x2,
            y2,
            _style_payload(style),
            _matrix_payload(transform),
        )

    def polygon(
        self,
        points: list[tuple[float, float]],
        style: StyleState,
        transform: Matrix2D,
        *,
        close: bool = True,
    ) -> None:
        self._call(
            "polygon drawing",
            self._require_canvas().polygon,
            points,
            _style_payload(style),
            _matrix_payload(transform),
            close,
        )

    def ellipse(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        style: StyleState,
        transform: Matrix2D,
    ) -> None:
        self._call(
            "ellipse drawing",
            self._require_canvas().ellipse,
            x,
            y,
            width,
            height,
            _style_payload(style),
            _matrix_payload(transform),
        )

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
        self._call(
            "arc drawing",
            self._require_canvas().arc,
            x,
            y,
            width,
            height,
            start,
            stop,
            mode,
            _style_payload(style),
            _matrix_payload(transform),
        )

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
        cache: bool = True,
    ) -> None:
        image_key = id(image)
        cached_version = self._image_cache_versions.get(image_key) if cache else None
        image_pixels = None if cached_version == image.version else image.pillow.tobytes()
        callback = getattr(self._require_canvas(), "draw_cached_image", None)
        if cache and callable(callback):
            self._call(
                "image drawing",
                callback,
                image_key,
                image.version,
                image_pixels,
                image.width,
                image.height,
                dx,
                dy,
                dw,
                dh,
                _style_payload(style),
                _matrix_payload(transform),
                source,
            )
            self._image_cache_versions[image_key] = image.version
            return
        self._call(
            "image drawing",
            self._require_canvas().draw_image,
            image_pixels if image_pixels is not None else image.pillow.tobytes(),
            image.width,
            image.height,
            dx,
            dy,
            dw,
            dh,
            _style_payload(style),
            _matrix_payload(transform),
            source,
        )

    def text(
        self,
        value: str,
        x: float,
        y: float,
        style: StyleState,
        transform: Matrix2D,
    ) -> None:
        if style.fill_color is None:
            return
        if abs(transform.b) <= _AFFINE_EPSILON and abs(transform.c) <= _AFFINE_EPSILON:
            self._draw_axis_aligned_text(value, x, y, style, transform)
            return
        from p5.backends.pillow import PillowRenderer

        text_renderer = PillowRenderer(self.width, self.height, self.pixel_density)
        text_renderer.clear()
        text_style = style.copy()
        text_style.erasing = False
        text_style.blend_mode = c.BLEND
        text_renderer.text(value, x, y, text_style, transform)
        self.draw_image(
            Image(text_renderer.get_image()),
            0,
            0,
            self.width,
            self.height,
            style,
            Matrix2D.identity(),
            cache=False,
        )

    def _draw_axis_aligned_text(
        self,
        value: str,
        x: float,
        y: float,
        style: StyleState,
        transform: Matrix2D,
    ) -> None:
        fill = style.fill_color
        if fill is None:
            return
        font_size = max(1, int(round(style.text_size * self.pixel_density)))
        physical_transform = Matrix2D.scaling(self.pixel_density).multiply(transform)
        lines = str(value).splitlines() or [""]
        for line_index, line in enumerate(lines):
            px, py = physical_transform.transform_point(x, y + line_index * style.text_leading)
            text_image, bbox = self._cached_text_image(line, style, font_size, fill.to_tuple())
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width <= 0 or height <= 0:
                continue
            if style.text_align_x == c.CENTER:
                px -= width / 2
            elif style.text_align_x == c.RIGHT:
                px -= width
            if style.text_align_y == c.CENTER:
                py -= height / 2
            elif style.text_align_y == c.BOTTOM:
                py -= height
            elif style.text_align_y == c.BASELINE:
                py -= self.text_ascent(style) * self.pixel_density
            left = max(0, floor(px + bbox[0]))
            top = max(0, floor(py + bbox[1]))
            right = min(self.physical_width, ceil(px + bbox[2]))
            bottom = min(self.physical_height, ceil(py + bbox[3]))
            if right <= left or bottom <= top:
                continue
            self.draw_image(
                text_image,
                left / self.pixel_density,
                top / self.pixel_density,
                text_image.width / self.pixel_density,
                text_image.height / self.pixel_density,
                style,
                Matrix2D.identity(),
            )

    def _cached_text_image(
        self,
        line: str,
        style: StyleState,
        font_size: int,
        fill: tuple[int, int, int, int],
    ) -> tuple[Image, tuple[int, int, int, int]]:
        key = (
            line,
            str(style.text_font.path) if style.text_font.path is not None else None,
            style.text_font.name,
            font_size,
            fill,
        )
        cached = self._text_image_cache.get(key)
        if cached is not None:
            return cached

        from PIL import Image as PILImage
        from PIL import ImageDraw

        font = style.text_font.pillow_font(font_size)
        draw_probe = ImageDraw.Draw(PILImage.new("RGBA", (1, 1), (0, 0, 0, 0)), "RGBA")
        bbox = draw_probe.textbbox((0, 0), line, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= 0 or height <= 0:
            text_image = Image(PILImage.new("RGBA", (1, 1), (0, 0, 0, 0)))
            cached = (text_image, (0, 0, 0, 0))
            self._text_image_cache[key] = cached
            return cached
        overlay = PILImage.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, "RGBA")
        draw.text((-bbox[0], -bbox[1]), line, fill=fill, font=font)
        cached = (Image(overlay), bbox)
        self._text_image_cache[key] = cached
        return cached

    def text_width(self, value: str, style: StyleState) -> float:
        from p5.backends.pillow import PillowRenderer

        return PillowRenderer(self.width or 1, self.height or 1, self.pixel_density).text_width(
            value, style
        )

    def text_ascent(self, style: StyleState) -> float:
        from p5.backends.pillow import PillowRenderer

        return PillowRenderer(self.width or 1, self.height or 1, self.pixel_density).text_ascent(
            style
        )

    def text_descent(self, style: StyleState) -> float:
        from p5.backends.pillow import PillowRenderer

        return PillowRenderer(self.width or 1, self.height or 1, self.pixel_density).text_descent(
            style
        )

    def load_pixels(self) -> list[int]:
        pixels = self._call("pixel readback", self._require_canvas().load_pixels)
        return list(pixels)

    def update_pixels(self, pixels: Sequence[int]) -> None:
        try:
            payload = bytes(pixels)
        except ValueError as exc:
            raise ArgumentValidationError(
                "Pixel values must be integers between 0 and 255."
            ) from exc
        self._call("pixel upload", self._require_canvas().update_pixels, payload)

    def blend_region(
        self,
        source_image: object | None,
        source: tuple[int, int, int, int],
        destination: tuple[int, int, int, int],
        mode: str,
    ) -> None:
        if isinstance(source_image, Image):
            source_image = source_image.pillow
        if source_image is None:
            self._call(
                "region blending",
                self._require_canvas().blend_region,
                None,
                None,
                None,
                source,
                destination,
                mode,
            )
            return
        convert = getattr(source_image, "convert", None)
        if callable(convert):
            source_image = convert("RGBA")
        width = getattr(source_image, "width", None)
        height = getattr(source_image, "height", None)
        tobytes = getattr(source_image, "tobytes", None)
        if not isinstance(width, int) or not isinstance(height, int) or not callable(tobytes):
            raise ArgumentValidationError("blend_region() source image must expose RGBA pixels.")
        self._call(
            "region blending",
            self._require_canvas().blend_region,
            tobytes(),
            width,
            height,
            source,
            destination,
            mode,
        )

    def save(self, path: str | Path) -> None:
        self._call("canvas export", self._require_canvas().save, str(path))

    def _canvas_type(self) -> type[Any]:
        canvas_type = getattr(self._canvas_module, "Canvas", None)
        if canvas_type is None:
            raise BackendCapabilityError(
                "The experimental 'canvas' backend found p5.rust._canvas, but the extension does "
                "not expose Canvas. Rebuild p5_canvas or select backend='headless'."
            )
        return canvas_type

    def _sync_dimensions(self) -> None:
        logical_width, logical_height, physical_width, physical_height, pixel_density = (
            self._require_canvas().dimensions()
        )
        self.width = int(logical_width)
        self.height = int(logical_height)
        self.physical_width = int(physical_width)
        self.physical_height = int(physical_height)
        self.pixel_density = float(pixel_density)

    def _require_canvas(self) -> Any:
        if self._canvas is None:
            raise BackendCapabilityError(
                "The experimental 'canvas' backend has not allocated a canvas yet. Call "
                "create_canvas() before drawing."
            )
        return self._canvas

    def _call(self, operation: str, callback: Callable[..., Any], *args: object) -> Any:
        try:
            return callback(*args)
        except ValueError as exc:
            raise ArgumentValidationError(str(exc)) from exc
        except RuntimeError as exc:
            raise BackendCapabilityError(
                f"The 'canvas' backend failed during {operation}: {exc}"
            ) from exc
