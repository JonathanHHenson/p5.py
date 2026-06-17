# Rust acceleration

`p5-py` keeps Rust optional. The Python package must work without compiling any
native extension, and accelerated functions must have deterministic Python
fallbacks with parity tests.

## Current scope

The first accelerated targets are narrow, pure computational paths:

- `noise_3d`: the Perlin-style noise core used by `p5.core.random.noise()`.
- `exclusion_blend_rgb`: the packed RGB byte loop used by the Pillow renderer's
  `EXCLUSION` blend mode.

These were selected because sketches commonly call noise once per point or pixel,
and per-pixel blend/filter loops are easy to isolate from renderer and backend
state. Both targets are pure functions, so they are low-risk seams for optional
native acceleration.

## Layout

```text
crates/
  p5_accel/
    Cargo.toml
    src/lib.rs
  p5_canvas/
    Cargo.toml
    src/lib.rs
src/p5/rust/
  __init__.py          # optional acceleration import, wrappers, Python fallbacks
  canvas.py            # optional canvas extension import and capability checks
  _accelerated.pyi     # type stub for p5.rust._accelerated
  _canvas.pyi          # type stub for p5.rust._canvas
  benchmarks.py        # local timing helpers
```

The acceleration extension module is named `p5.rust._accelerated`. The canvas
foundation extension module is named `p5.rust._canvas`. Importing `p5.rust`
never requires either extension to exist.

## Local build

From the repository root, install the normal Python development environment:

```sh
uv sync --dev
```

Build the existing acceleration extension into the active environment with the
default maturin settings:

```sh
uvx maturin develop --release
```

The `pyproject.toml` `[tool.maturin]` settings point maturin at
`crates/p5_accel/Cargo.toml` and install the extension as
`p5.rust._accelerated` under the `src` Python source tree.

Build the canvas foundation extension explicitly so it coexists with
`p5_accel` without changing the default maturin target:

```sh
uvx maturin develop --release --manifest-path crates/p5_canvas/Cargo.toml --module-name p5.rust._canvas --python-source src --features extension-module
```

You can confirm which acceleration implementation is active with:

```sh
uv run python -c "import p5.rust as r; print(r.health_check())"
```

Expected values are:

- `rust-accelerated` when the acceleration extension is importable.
- `python-fallback` when the acceleration extension is absent.

You can confirm the canvas bridge health with:

```sh
uv run python -c "from p5.rust.canvas import canvas_health_check; print(canvas_health_check())"
```

Expected values are:

- `rust-canvas` when the canvas extension is importable.
- `unavailable` when the canvas extension is absent.

## Packaging commands

Build a Rust-acceleration-backed wheel locally with the default maturin target:

```sh
uvx maturin build --release
```

Build a canvas-extension-backed wheel explicitly with:

```sh
uvx maturin build --release --manifest-path crates/p5_canvas/Cargo.toml --module-name p5.rust._canvas --python-source src --features extension-module
```

The default pure-Python build remains hatchling-based, so users and CI jobs that
do not build Rust still receive the Python fallback behavior. The `canvas`
backend is opt-in and raises `BackendCapabilityError` when selected without the
`p5.rust._canvas` extension.

## Tests and parity checks

Run the Rust acceleration test slice with:

```sh
uv run pytest tests/unit/test_rust_acceleration.py
```

Run the Rust canvas bridge test slice with:

```sh
uv run pytest tests/unit/test_rust_canvas.py tests/contracts/test_canvas_backend.py
cargo test --manifest-path crates/p5_canvas/Cargo.toml
```

Run the full Python validation suite with:

```sh
uv run ruff check .
uv run pytest
```

If Rust is built, the same tests compare the extension results against the Python
reference implementations. Current parity expectations are an absolute tolerance
of `1e-12` for `noise_3d` and exact byte-for-byte equality for
`exclusion_blend_rgb`. If Rust is not built, the tests still verify the fallback
paths and strategy selection.

## Benchmarks

Run small local timing helpers with:

```sh
uv run python -m p5.rust.benchmarks
```

The benchmark output reports both the wrapper path and the explicit Python
fallback path. Treat the timings as local smoke/profiling data rather than stable
performance guarantees. When Rust is unavailable, the wrapper path is expected to
use the same Python fallback and should not show a meaningful speedup.
