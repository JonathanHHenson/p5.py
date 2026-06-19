# Core Concepts

## Canvas

`create_canvas(width, height)` creates the drawing surface. `width()` and
`height()` return the logical canvas size.

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

Use `push()` and `pop()` to isolate temporary style or transform changes:

```python
p5.push()
p5.translate(200, 100)
p5.rotate(0.5)
p5.rect(0, 0, 80, 40)
p5.pop()
```

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

