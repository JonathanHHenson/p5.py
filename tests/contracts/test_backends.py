from p5.backends import available_backends, create_backend, register_backend
from p5.backends.headless import HeadlessBackend


def test_default_backends_are_registered():
    assert "canvas" in available_backends()
    assert "headless" in available_backends()
    assert "pillow" in available_backends()
    assert "pyglet" in available_backends()


def test_custom_backend_registration():
    register_backend("custom-test", HeadlessBackend)
    backend = create_backend("custom-test")
    assert isinstance(backend, HeadlessBackend)
