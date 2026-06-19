import pytest

import p5
from p5.exceptions import ArgumentValidationError


def test_global_mode_explicit_callbacks():
    frames = []

    def setup():
        p5.create_canvas(16, 12)
        p5.background(0)

    def draw():
        frames.append(p5.frame_count())
        p5.fill(255, 0, 0)
        p5.no_stroke()
        p5.circle(8, 6, 6)

    context = p5.run(setup=setup, draw=draw, headless=True, max_frames=2)

    assert frames == [0, 1]
    assert context.width == 16
    assert context.height == 12
    assert context.frame_count == 2


def test_camel_case_aliases_are_not_exported():
    assert not hasattr(p5, "createCanvas")
    assert not hasattr(p5, "noStroke")
    assert not hasattr(p5, "imageSampling")


def test_image_sampling_api():
    def setup():
        p5.create_canvas(4, 4)
        assert p5.image_sampling() == p5.LINEAR
        p5.no_smooth()
        assert p5.image_sampling() == p5.NEAREST
        p5.smooth()
        assert p5.image_sampling() == p5.LINEAR
        p5.image_sampling(p5.NEAREST)
        assert p5.image_sampling() == p5.NEAREST
        p5.smooth()
        with pytest.raises(ArgumentValidationError):
            p5.image_sampling("bogus")

    p5.run(setup=setup, draw=lambda: None, headless=True, max_frames=0)
