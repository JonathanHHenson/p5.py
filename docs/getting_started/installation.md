# Installation

Install the package from PyPI:

```sh
pip install p5py-vibe
```

Then import it as `p5`:

```python
import p5
```

Optional media helpers are available through the `media` extra:

```sh
pip install "p5py-vibe[media]"
```

## Check Your Install

Save this as `hello_p5.py`:

```python
import p5


def setup() -> None:
    p5.create_canvas(200, 200)


def draw() -> None:
    p5.background(240)
    p5.fill(30, 120, 220)
    p5.circle(100, 100, 80)


p5.run(setup=setup, draw=draw)
```

Run it:

```sh
python hello_p5.py
```

If your environment does not support a native window, run a bounded headless
render:

```sh
python hello_p5.py --headless --frames 1
```

## Local Repository Setup

If you are working from this repository, use `uv`:

```sh
uv sync --dev
uvx maturin develop --manifest-path crates/p5_canvas/Cargo.toml --module-name p5.rust._canvas --python-source src --features extension-module
uv run python examples/01_getting_started/basic_shapes.py --headless --frames 1
```

