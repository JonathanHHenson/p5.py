# Examples

Examples live in [../../examples](../../examples).

Useful starting points:

- `examples/01_getting_started/basic_shapes.py`
- `examples/01_getting_started/timing_and_animation.py`
- `examples/02_drawing/shapes_curves.py`
- `examples/02_drawing/pixels_and_export.py`
- `examples/03_assets/images_and_sprites.py`
- `examples/05_interaction/input_state.py`
- `examples/08_3d/webgl_scene.py`
- `examples/games/asteroids.py`

Run an example interactively:

```sh
uv run python examples/01_getting_started/basic_shapes.py --interactive
```

Run a bounded headless preview:

```sh
uv run python examples/01_getting_started/basic_shapes.py --headless --frames 1
```

Most examples save output to `examples/output/` when `--frames` is provided.
Pass `--no-save` to skip image export.

