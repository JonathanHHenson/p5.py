from __future__ import annotations

import pytest

from p5.backends import available_backends, create_backend, get_backend_class
from p5.backends.canvas import CanvasBackend
from p5.exceptions import BackendCapabilityError
from p5.rust import canvas as canvas_bridge


def test_canvas_backend_is_registered_as_opt_in_backend() -> None:
    assert "canvas" in available_backends()
    assert get_backend_class("canvas") is CanvasBackend


def test_canvas_backend_selection_requires_rust_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(canvas_bridge, "_canvas", None)
    monkeypatch.setattr(canvas_bridge, "_CANVAS_IMPORT_ERROR", ImportError("missing _canvas"))

    with pytest.raises(BackendCapabilityError, match="p5.rust._canvas"):
        create_backend("canvas")
