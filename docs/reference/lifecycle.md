# Sketch Lifecycle

## Function Mode

```python
import p5


def preload() -> None:
    pass


def setup() -> None:
    p5.create_canvas(400, 300)


def draw() -> None:
    p5.background(255)


p5.run(preload=preload, setup=setup, draw=draw)
```

## Class Mode

Subclass `p5.Sketch` when you prefer object-oriented sketches:

```python
import p5


class MySketch(p5.Sketch):
    def setup(self) -> None:
        self.create_canvas(400, 300)

    def draw(self) -> None:
        self.background(255)


MySketch().run()
```

## Lifecycle Functions

- `run(setup=None, draw=None, preload=None, headless=None, max_frames=None)`
- `no_loop()`
- `loop()`
- `redraw()`
- `is_looping()`
- `frame_count()`
- `frame_rate(fps=None)`
- `get_target_frame_rate()`
- `delta_time()`
- `millis()`

## Canvas Size

- `create_canvas(width, height, renderer=P2D, pixel_density=None)`
- `resize_canvas(width, height, pixel_density=None)`
- `width()`
- `height()`
- `window_width()`
- `window_height()`
- `display_width()`
- `display_height()`
- `pixel_density(value=None)`
- `display_density()`

