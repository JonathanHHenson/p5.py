# Your First Sketch

> [!IMPORTANT]
> This archived page shows the old `p5` package API. For maintained releases,
> install [gummy-snake](https://pypi.org/project/gummy-snake/) and use
> `import gummysnake as gs`. Active development lives at
> [github.com/JonathanHHenson/gummy_snake](https://github.com/JonathanHHenson/gummy_snake).

A sketch usually has two functions:

- `setup()` runs once.
- `draw()` runs every frame.

```python
import p5


@p5.setup
def setup() -> None:
    p5.create_canvas(500, 300)
    p5.no_stroke()


@p5.draw
def draw() -> None:
    p5.background(245)
    p5.fill(255, 80, 80)
    p5.circle(250, 150, 120)


p5.run()
```

The decorators register callbacks on the current sketch module. You can also
use `app = p5.sketch()` when you want a local sketch object, or pass callbacks
explicitly to `p5.run(...)` for compatibility with older examples.

## Animate It

Use `frame_count()` to change values over time:

```python
import p5


@p5.setup
def setup() -> None:
    p5.create_canvas(500, 300)


@p5.draw
def draw() -> None:
    p5.background(20)
    x = 250 + p5.sin(p5.current.frame_count * 0.05) * 120
    p5.fill(80, 180, 255)
    p5.circle(x, 150, 60)


p5.run()
```

## Draw Once

Call `no_loop()` in `setup()` when the sketch only needs one frame:

```python
def setup() -> None:
    p5.create_canvas(400, 400)
    p5.no_loop()
```

## Async Setup

Lifecycle and event callbacks may be `async def`, so sketches can await
async-compatible asset helpers:

```python
import p5

sprite = None


@p5.preload
async def preload() -> None:
    global sprite
    sprite = await p5.load_image_async("assets/sprite.png")
```
