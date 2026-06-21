# API Reference

> [!IMPORTANT]
> This API reference is archived for `p5py` / `p5py-vibe`. The maintained
> project is **Gummy Snake** at
> [github.com/JonathanHHenson/gummy_snake](https://github.com/JonathanHHenson/gummy_snake),
> published on PyPI as [gummy-snake](https://pypi.org/project/gummy-snake/).
> New code should use `import gummysnake as gs`.

The archived public package is imported as `p5`:

```python
import p5
```

Reference topics:

- [Sketch lifecycle](lifecycle.md)
- [Canvas and drawing](drawing.md)
- [Color, style, and transforms](style_and_transforms.md)
- [Images, pixels, and assets](assets_and_pixels.md)
- [Input and events](input_and_events.md)
- [Math, random, and vectors](math_random_vectors.md)
- [3D and shaders](three_d.md)
- [Constants and enums](constants_and_enums.md)
- [Compatibility and unsupported APIs](compatibility.md)

Function names use Python `snake_case`. p5.js-style camelCase names are not
public APIs.

Python-first conveniences are part of the public API:

- decorator callbacks with `@p5.setup`, `@p5.draw`, and `@p5.on(...)`
- property facades such as `p5.current`, `p5.mouse`, and `p5.keyboard`
- context managers such as `p5.style(...)` and `p5.transform(...)`
- async-compatible lifecycle callbacks and asset loaders
- vector operators, event vector properties, and image indexing
