from __future__ import annotations

import pytest

from p5.backends.canvas import CanvasBackend
from p5.backends.canvas_renderer import CanvasRenderer
from p5.exceptions import BackendCapabilityError
from p5.rust import canvas as canvas_bridge
from p5.rust.canvas import (
    canvas_health_check,
    canvas_import_error,
    is_canvas_available,
    require_canvas_extension,
)


class FakeCanvasModule:
    def health_check(self) -> str:
        return "fake-canvas"


def test_canvas_health_check_reports_unavailable_or_extension() -> None:
    assert canvas_health_check() in {"unavailable", "rust-canvas"}
    assert is_canvas_available() in {True, False}
    assert canvas_import_error() is None or isinstance(canvas_import_error(), ImportError)


def test_canvas_wrapper_uses_loaded_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeCanvasModule()
    monkeypatch.setattr(canvas_bridge, "_canvas", fake)
    monkeypatch.setattr(canvas_bridge, "_CANVAS_IMPORT_ERROR", None)

    assert is_canvas_available()
    assert canvas_health_check() == "fake-canvas"
    assert require_canvas_extension() is fake


def test_canvas_wrapper_raises_capability_error_when_extension_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(canvas_bridge, "_canvas", None)
    monkeypatch.setattr(canvas_bridge, "_CANVAS_IMPORT_ERROR", ImportError("missing _canvas"))

    with pytest.raises(BackendCapabilityError, match="p5.rust._canvas"):
        require_canvas_extension()


def test_canvas_backend_reports_conservative_capabilities() -> None:
    capabilities = CanvasBackend.capabilities

    assert capabilities.interactive is False
    assert capabilities.headless is False
    assert capabilities.text is False
    assert capabilities.images is False
    assert capabilities.pixels is False
    assert capabilities.pixel_readback is False
    assert capabilities.pixel_update is False
    assert capabilities.canvas_export is False
    assert capabilities.mouse is False
    assert capabilities.keyboard is False
    assert capabilities.touch is False
    assert capabilities.paths is False
    assert capabilities.transforms is False
    assert capabilities.blend_modes == frozenset()
    assert capabilities.three_d is False
    assert capabilities.shaders is False
    assert capabilities.sound is False


def test_canvas_backend_skeleton_raises_for_unimplemented_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(canvas_bridge, "_canvas", FakeCanvasModule())
    monkeypatch.setattr(canvas_bridge, "_CANVAS_IMPORT_ERROR", None)

    backend = CanvasBackend()

    assert backend.health_check() == "fake-canvas"
    with pytest.raises(BackendCapabilityError, match="canvas creation"):
        backend.create_canvas(100, 100)
    with pytest.raises(BackendCapabilityError, match="frame scheduling"):
        backend.run(object())  # type: ignore[arg-type]


def test_canvas_renderer_skeleton_raises_for_unimplemented_operations() -> None:
    renderer = CanvasRenderer(FakeCanvasModule())

    with pytest.raises(BackendCapabilityError, match="canvas allocation"):
        renderer.resize(100, 100)
    with pytest.raises(BackendCapabilityError, match="pixel readback"):
        renderer.load_pixels()
