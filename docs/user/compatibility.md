# Compatibility and Pythonic differences

`p5-py` borrows p5's sketching model while intentionally presenting an opinionated Pythonic API rather than a browser-compatible API surface.

## Naming

Public APIs use `snake_case` only:

- `create_canvas()`
- `frame_rate()`
- `no_loop()`
- `pixel_density()`

p5.js-style camelCase aliases such as `createCanvas()`, `frameRate()`, `noLoop()`, and `pixelDensity()` are intentionally not exported.

## Same ideas, different runtime

Expected differences from browser p5.js include:

- no DOM helpers
- no HTML elements
- no browser event loop
- no browser fetch/storage assumptions
- Python exceptions instead of loose browser-style failures

## Unsupported and excluded APIs

The package intentionally excludes browser-only areas such as:

- DOM element helpers such as `create_div()` and `create_button()`
- `p5.XML`
- `p5.Table` and `p5.TableRow`
- browser-only APIs with no native Python equivalent

These compatibility stubs raise explicit `p5` exceptions so unsupported features fail clearly.

## Migration guidance

When porting small p5.js sketches:

1. keep the `setup()`/`draw()` structure
2. switch imports to `import p5`
3. convert p5.js-style camelCase calls to p5-py's snake_case API
4. replace browser/DOM code with native Python alternatives or remove it
5. use `headless` for deterministic tests while porting

See `tests/unit/test_compatibility.py` for representative compatibility expectations.
