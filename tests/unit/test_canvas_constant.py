import p5
from p5 import constants as c


def test_canvas_backend_constant_is_public() -> None:
    assert c.CANVAS == "canvas"
    assert p5.CANVAS == "canvas"
