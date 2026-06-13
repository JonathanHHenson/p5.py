import math
from typing import Any, cast

import pytest

import p5_py as p5
from p5_py.backends.headless import HeadlessBackend
from p5_py.context import SketchContext
from p5_py.events.input_state import MouseEvent
from p5_py.exceptions import ArgumentValidationError
from p5_py.sketch import Sketch


class _WebGLSketch(Sketch):
    def __init__(self):
        super().__init__(backend="headless")


def make_context() -> SketchContext:
    sketch = _WebGLSketch()
    context = SketchContext(sketch, HeadlessBackend())
    sketch.context = context
    context.create_canvas(96, 96, renderer=p5.WEBGL)
    return context


def _camera_radius(context: SketchContext) -> float:
    offset_x = context._camera3d.eye.x - context._camera3d.target.x
    offset_y = context._camera3d.eye.y - context._camera3d.target.y
    offset_z = context._camera3d.eye.z - context._camera3d.target.z
    return math.sqrt(offset_x * offset_x + offset_y * offset_y + offset_z * offset_z)


def test_orbit_control_rotates_camera_from_accumulated_mouse_drag():
    context = make_context()
    initial_eye = context._camera3d.eye
    initial_radius = _camera_radius(context)

    context.dispatch_mouse_event(MouseEvent(x=8, y=8, button="left", type="mouse_pressed"))
    context.dispatch_mouse_event(
        MouseEvent(x=18, y=2, dx=10, dy=-6, button="left", type="mouse_dragged")
    )

    camera = context.orbit_control()

    assert camera.eye != initial_eye
    assert _camera_radius(context) == pytest.approx(initial_radius)

    camera_after_second_call = context.orbit_control()
    assert camera_after_second_call.eye.x == pytest.approx(camera.eye.x)
    assert camera_after_second_call.eye.y == pytest.approx(camera.eye.y)
    assert camera_after_second_call.eye.z == pytest.approx(camera.eye.z)


def test_orbit_control_applies_mouse_wheel_zoom():
    context = make_context()
    initial_radius = _camera_radius(context)

    context.dispatch_mouse_event(MouseEvent(x=0, y=0, scroll_y=2.0, type="mouse_wheel"))
    context.orbit_control()

    assert _camera_radius(context) < initial_radius


def test_texture_requires_p5_image_and_material_apis_clear_bound_texture():
    context = make_context()

    with pytest.raises(ArgumentValidationError, match="p5_py Image"):
        context.texture(cast(Any, object()))

    checker = p5.create_image(2, 2)
    context.texture(checker)
    assert context._effective_3d_material().texture is not None

    context.ambient_material(255)
    assert context._effective_3d_material().texture is None
