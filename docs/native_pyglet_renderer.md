# Native Pyglet renderer plan

## Current state

The current interactive Pyglet backend is a bridge backend:

```text
p5-py public API
  ↓
SketchContext
  ↓
PillowRenderer
  ↓
PygletBackend uploads/presents the Pillow image in a Pyglet window
```

This was useful for the first implementation because it gave p5-py one deterministic renderer for both tests and interactive sketches. It also let the project validate the runtime, global API, drawing state, transforms, paths, pixel APIs, exports, and HiDPI behavior without committing early to Pyglet graphics internals.

The downside is that the interactive backend is not yet truly native. It still rasterizes through Pillow and uploads a frame image to Pyglet.

## Target state

The target architecture separates the window/event backend from the renderer:

```text
p5-py public API
  ↓
SketchContext
  ↓
Renderer protocol
  ↓
PygletRenderer
  ↓
Pyglet/OpenGL framebuffer
```

With this split:

- `PygletBackend` owns the window, event loop, input events, resize events, frame scheduling, and shutdown.
- `PygletRenderer` owns native drawing operations.
- `SketchContext` continues to depend only on the renderer/backend protocols.
- The public API remains unchanged.
- Pillow remains the deterministic headless renderer and export/golden-test path.

## Proposed module layout

The current single-file backend can later be split into a package:

```text
src/p5_py/backends/pyglet/
  __init__.py
  backend.py
  renderer.py
  events.py
  capabilities.py
```

A smaller first step could keep the existing backend file and add:

```text
src/p5_py/backends/pyglet_renderer.py
```

## Responsibilities

### `PygletBackend`

Responsible for:

- creating the native window
- detecting display density / framebuffer size
- running the Pyglet event loop
- scheduling frames
- normalizing mouse and keyboard events
- forwarding resize and close events
- exposing backend capabilities

Not responsible for:

- parsing p5-style arguments
- managing drawing style state
- implementing p5.js aliases
- owning sketch lifecycle semantics
- deciding fill/stroke behavior

### `PygletRenderer`

Responsible for:

- `begin_frame` / `end_frame`
- `background` and `clear`
- points, lines, polygons, rectangles, ellipses, arcs
- fill and stroke rendering
- transform application
- HiDPI coordinate mapping
- image/text support when those epics are implemented
- pixel/export capability handling

## Rendering approach options

### Pyglet shapes

Pros:

- simple first implementation
- clean dependency story
- works with Pyglet's supported public APIs

Cons:

- may not support all stroke joins/caps/fill rules needed for p5 fidelity
- complex paths may require flattening and triangulation

### Batched vertex lists

Pros:

- better performance than recreating shapes every frame
- more control over geometry

Cons:

- more renderer complexity
- requires careful lifecycle and batching design

### Direct OpenGL or ModernGL-style rendering

Pros:

- best long-term performance/control
- natural path toward WEBGL-like features later

Cons:

- larger implementation scope
- shader and context management complexity
- more difficult to keep beginner-friendly and cross-platform

## Recommended first native renderer milestone

Start with Pyglet-native shapes and shared p5-py geometry helpers.

Implement first:

- `background`
- `clear`
- `point`
- `line`
- `polygon`
- `rect`
- `square`
- `ellipse`
- `circle`
- `triangle`
- `quad`
- `arc`

Reuse existing geometry flattening for:

- Bezier curves
- quadratic curves
- custom shapes
- arcs where native support is insufficient

## HiDPI behavior

The native renderer must preserve the current pixel-density model:

- `width()` and `height()` are logical p5 canvas dimensions.
- `display_density()` reports the native display density when available.
- `pixel_density()` controls the logical-to-physical scale.
- Pyglet native drawing should not double-scale on Retina displays.

The renderer should define one clear coordinate transform from logical p5 coordinates to framebuffer coordinates.

## Pixel and export APIs

The native renderer should either implement or capability-gate:

- `load_pixels`
- `update_pixels`
- `save_canvas`

Potential approaches:

- framebuffer readback for `load_pixels` and `save_canvas`
- texture upload/update for `update_pixels`
- explicit `BackendCapabilityError` for unsupported pixel operations in the first native renderer milestone

Pillow should remain the canonical deterministic path for headless rendering, image export, and golden tests.

## Migration plan

1. Add `PygletRenderer` while keeping the current Pillow bridge backend intact.
2. Implement basic primitive rendering natively.
3. Add transform/path/curve support.
4. Preserve and test HiDPI behavior.
5. Decide pixel/export behavior.
6. Switch `PygletBackend` to use `PygletRenderer` by default.
7. Remove the bridge code or expose it as an explicit fallback backend.
8. Update docs and examples to describe native Pyglet rendering as the interactive default.
