# Compatibility and Unsupported APIs

p5py follows the p5 sketch model, but it is a Python package, not a browser
runtime.

## Naming

Use Python `snake_case`:

```python
p5.create_canvas(400, 300)
p5.frame_rate(30)
p5.no_loop()
```

Do not use p5.js camelCase names such as `createCanvas()`, `frameRate()`, or
`noLoop()`.

## Excluded Browser Features

The package does not implement:

- DOM element helpers
- browser storage and URL helpers
- `p5.XML`
- `p5.Table`
- `p5.TableRow`
- browser-only Web APIs

Unsupported compatibility stubs raise package-specific exceptions instead of
failing indirectly.

## Runtime Requirements

The Rust `p5_canvas` extension is required. Bounded/headless rendering,
interactive rendering, image loading, pixels, text, and export all route through
the canvas runtime.

