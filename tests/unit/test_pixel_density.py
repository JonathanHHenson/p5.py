from pathlib import Path

import pytest

import p5
from p5.backends.pillow import PillowRenderer
from p5.exceptions import ArgumentValidationError


def test_pillow_renderer_tracks_logical_and_physical_sizes():
    renderer = PillowRenderer(100, 50, pixel_density=2)

    assert renderer.width == 100
    assert renderer.height == 50
    assert renderer.physical_width == 200
    assert renderer.physical_height == 100
    assert renderer.get_image().size == (200, 100)


def test_pillow_renderer_scales_logical_coordinates():
    renderer = PillowRenderer(20, 20, pixel_density=2)
    from p5.core.color import Color
    from p5.core.state import StyleState
    from p5.core.transform import Matrix2D

    style = StyleState(fill_color=Color(255, 0, 0), stroke_color=None)
    renderer.polygon([(1, 1), (4, 1), (4, 4), (1, 4)], style, Matrix2D.identity())

    assert renderer.get_image().getpixel((2, 2)) == (255, 0, 0, 255)
    assert renderer.get_image().getpixel((8, 8)) == (255, 0, 0, 255)


def test_global_pixel_density_controls_backing_buffer(tmp_path: Path):
    output = tmp_path / "density.png"

    def setup():
        p5.create_canvas(10, 8, pixel_density=2)
        assert p5.width() == 10
        assert p5.height() == 8
        assert p5.pixel_density() == 2
        assert p5.display_density() == 1

    def draw():
        p5.background(255)
        p5.save_canvas(str(output))

    context = p5.run(setup=setup, draw=draw, backend="headless", max_frames=1)

    assert context.state.canvas.physical_width == 20
    assert context.state.canvas.physical_height == 16
    assert len(context.load_pixels()) == 20 * 16 * 4
    assert output.exists()


def test_pixel_density_alias_and_validation():
    def setup():
        p5.createCanvas(10, 10)
        assert p5.pixelDensity() == 1
        p5.pixelDensity(2)
        assert p5.pixel_density() == 2
        assert p5.displayDensity() == 1
        with pytest.raises(ArgumentValidationError):
            p5.pixel_density(0)

    p5.run(setup=setup, draw=lambda: None, backend="headless", max_frames=0)
