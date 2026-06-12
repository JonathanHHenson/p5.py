from p5_py.backends.pyglet import PygletBackend


class FakeFramebufferWindow:
    def get_framebuffer_size(self):
        return 1280, 840


class FakePixelRatioWindow:
    def get_pixel_ratio(self):
        return 2.0


class FakePygletModule:
    class window:
        @staticmethod
        def Window(width, height, caption):
            return FakePixelRatioWindow()


class FakeFramebufferPygletModule:
    class window:
        @staticmethod
        def Window(width, height, caption):
            return FakeFramebufferWindow()


def test_pyglet_presentation_size_uses_framebuffer_size():
    backend = PygletBackend()
    backend.renderer.resize(640, 420)
    backend._window = FakeFramebufferWindow()

    assert backend._presentation_size() == (1280, 840)


def test_pyglet_presentation_size_falls_back_to_pixel_ratio():
    backend = PygletBackend()
    backend.renderer.resize(640, 420)
    backend._window = FakePixelRatioWindow()

    assert backend._presentation_size() == (1280, 840)


def test_pyglet_create_canvas_defaults_to_display_density():
    backend = PygletBackend()
    backend._pyglet = FakePygletModule()

    backend.create_canvas(640, 420)

    assert backend.renderer.width == 640
    assert backend.renderer.height == 420
    assert backend.renderer.pixel_density == 2
    assert backend.renderer.physical_width == 1280
    assert backend.renderer.physical_height == 840


def test_pyglet_create_canvas_uses_framebuffer_density_fallback():
    backend = PygletBackend()
    backend._pyglet = FakeFramebufferPygletModule()

    backend.create_canvas(640, 420)

    assert backend.renderer.pixel_density == 2
    assert backend.renderer.physical_width == 1280
    assert backend.renderer.physical_height == 840
