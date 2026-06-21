# Getting Started

> [!IMPORTANT]
> These getting-started docs are archived. `p5py` / `p5py-vibe` is now
> **Gummy Snake**. Use the maintained project at
> [github.com/JonathanHHenson/gummy_snake](https://github.com/JonathanHHenson/gummy_snake)
> and install it with `pip install gummy-snake`. New sketches should import
> `gummysnake` rather than `p5`.

p5py is a Python creative-coding package. You write normal Python functions,
call drawing commands such as `circle()` and `background()`, and let p5py run the
sketch lifecycle.

Start here:

1. [Installation](installation.md)
2. [Your first sketch](first_sketch.md)
3. [Core concepts](core_concepts.md)
4. [Examples and next steps](examples.md)

## Tiny Example

```python
import p5


def setup() -> None:
    p5.create_canvas(320, 240)


def draw() -> None:
    p5.background(250)
    p5.circle(160, 120, 80)


p5.run(setup=setup, draw=draw)
```
