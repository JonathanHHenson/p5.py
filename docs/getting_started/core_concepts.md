# Core Concepts

## Canvas

`create_canvas(width, height)` creates the drawing surface. `p5.current.width`
and `p5.current.height` return the logical canvas size while a sketch is active.
The older `width()` and `height()` functions remain available.

```python
p5.create_canvas(640, 360)
```

Use `pixel_density()` when you need to control the physical backing buffer for
HiDPI output.

## State

Drawing commands use the current style and transform state:

```python
p5.fill(255, 0, 0)
p5.no_stroke()
p5.circle(100, 100, 50)
```

Use `style()` and `transform()` context managers to isolate temporary style or
transform changes:

```python
with p5.style(fill=(255, 0, 0), stroke=None):
    p5.circle(100, 100, 50)

with p5.transform(translate=(200, 100), rotate=0.5):
    p5.rect(0, 0, 80, 40)
```

`push()` / `pop()` and `with p5.pushed():` are also available when you need
manual control over the full drawing state stack.

## Headless Runs

Headless runs use the same Rust canvas runtime, but draw offscreen for tests,
CI, export, and repeatable scripts:

```sh
python my_sketch.py --headless --frames 1
```

## Python Names

p5py uses Python-style names:

```python
p5.create_canvas(400, 300)
p5.frame_rate(30)
p5.no_loop()
```

CamelCase p5.js names such as `createCanvas()` are not public p5py APIs.

New examples prefer decorator callbacks, property-style state access, and
Python data-model conveniences such as vector operators and image indexing.
