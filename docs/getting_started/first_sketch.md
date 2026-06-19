# Your First Sketch

A sketch usually has two functions:

- `setup()` runs once.
- `draw()` runs every frame.

```python
import p5


def setup() -> None:
    p5.create_canvas(500, 300)
    p5.no_stroke()


def draw() -> None:
    p5.background(245)
    p5.fill(255, 80, 80)
    p5.circle(250, 150, 120)


p5.run(setup=setup, draw=draw)
```

## Animate It

Use `frame_count()` to change values over time:

```python
import p5


def setup() -> None:
    p5.create_canvas(500, 300)


def draw() -> None:
    p5.background(20)
    x = 250 + p5.sin(p5.frame_count() * 0.05) * 120
    p5.fill(80, 180, 255)
    p5.circle(x, 150, 60)


p5.run(setup=setup, draw=draw)
```

## Draw Once

Call `no_loop()` in `setup()` when the sketch only needs one frame:

```python
def setup() -> None:
    p5.create_canvas(400, 400)
    p5.no_loop()
```

