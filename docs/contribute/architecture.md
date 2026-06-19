# Architecture

p5py keeps sketch semantics in Python and delegates canvas work to Rust.

```mermaid
flowchart LR
    subgraph Python
        User[setup/draw callbacks]
        Global[p5.api.global_mode]
        Sketch[Sketch]
        Context[SketchContext]
        State[SketchState]
        Backend[CanvasBackend]
        Renderer[CanvasRenderer]
    end

    subgraph Rust
        Wrapper[p5.rust.canvas]
        Extension[p5.rust._canvas]
        Canvas[p5_canvas crate]
    end

    User --> Global --> Context
    User --> Sketch --> Context
    Context --> State
    Context --> Backend
    Context --> Renderer
    Backend --> Wrapper --> Extension --> Canvas
    Renderer --> Wrapper
```

## The Core Objects

The runtime has a small set of objects that appear in most changes:

| Object | File | Responsibility |
| --- | --- | --- |
| `Sketch` | `src/p5/sketch.py` | Owns lifecycle ordering, callback dispatch, and the run loop entry point for class-mode sketches. |
| `FunctionSketch` | `src/p5/sketch.py` | Wraps module-level `setup()`, `draw()`, and event callbacks so function-mode sketches use the same lifecycle as class-mode sketches. |
| `SketchContext` | `src/p5/context.py` | Runtime controller for one sketch. It validates high-level p5 operations, updates `SketchState`, calls plugins, and sends drawing work to the renderer. |
| `SketchState` | `src/p5/core/state.py` | Mutable data for one sketch: canvas dimensions, style, transforms, timing, input, shape-building state, and lifecycle flags. |
| `CanvasBackend` | `src/p5/backends/canvas.py` | Runtime adapter. It chooses headless vs interactive execution, opens native windows when supported, schedules frames, and dispatches input events. |
| `CanvasRenderer` | `src/p5/backends/canvas_renderer.py` | Drawing adapter. It translates Python state and drawing requests into payloads understood by the Rust canvas extension. |
| `p5.rust.canvas` | `src/p5/rust/canvas.py` | Import and capability wrapper for the PyO3 extension. It turns missing native support into clear p5 errors. |
| `p5_canvas` | `crates/p5_canvas/` | Required Rust canvas runtime and renderer implementation. |

## Ownership Boundaries

Python owns:

- public API naming and validation
- `setup()`, `draw()`, and callback ordering
- global-mode context activation
- sketch state, style state, transforms, and plugin hooks
- backend and renderer adapter contracts

Rust owns:

- canvas allocation and drawing
- presentation and export
- image asset loading and saving
- text, pixels, and readback
- native window and input events when compiled with those capabilities

## Sketch, Context, and State

These names are close enough to be confusing:

- `Sketch` is the user-program object and lifecycle owner.
- `SketchContext` is the active runtime controller for that sketch.
- `SketchState` is the mutable data inside the context.

In code, that relationship looks like this:

```mermaid
classDiagram
    class Sketch {
        +preload()
        +setup()
        +draw()
        +run()
        +stop()
    }

    class SketchContext {
        +state: SketchState
        +backend
        +renderer
        +create_canvas()
        +fill()
        +circle()
        +load_pixels()
    }

    class SketchState {
        +canvas
        +style
        +transform
        +timing
        +input
        +stack
    }

    Sketch --> SketchContext : creates and activates
    SketchContext --> SketchState : owns mutable data
```

`SketchContext` methods are where most p5 semantics live. For example,
`SketchContext.rect()` resolves the current rectangle mode and style before
asking the renderer to draw. `SketchState` does not draw and does not validate
public API calls; it only stores the values those methods need.

## What Sketch State Means

`SketchState` is the mutable Python data model for one running sketch. It is not
the sketch object itself, and it is not the Rust canvas. It is the place where
p5py stores the current p5-style settings that affect later API calls.

For example:

```python
p5.fill(255, 0, 0)
p5.no_stroke()
p5.circle(100, 100, 40)
```

`fill()` and `no_stroke()` update `SketchContext.state.style`. When `circle()`
runs, `SketchContext` reads that style state, combines it with the current
transform and color mode, and asks `CanvasRenderer` to draw the circle.

`SketchState` is defined in `src/p5/core/state.py` and contains:

- `canvas`: logical size, physical size, pixel density, renderer kind, and
  whether a canvas has been created.
- `color_mode`: current RGB, HSB, or HSL interpretation and channel ranges.
- `style`: fill, stroke, stroke weight, text style, image mode, blend mode, and
  related drawing settings.
- `transform`: the current 2D transform matrix.
- `shape`: temporary vertices while `begin_shape()` / `end_shape()` is active.
- `timing`: `frame_count`, `delta_time`, target frame rate, and elapsed time.
- `input`: current mouse, keyboard, and touch values.
- `stack`: saved style and transform entries for `push()` / `pop()`.
- `looping` and `redraw_requested`: frame scheduling flags.

```mermaid
flowchart TD
    A[p5.fill red] --> B[SketchContext.state.style.fill_color]
    C[p5.translate] --> D[SketchContext.state.transform.matrix]
    E[p5.circle] --> F[SketchContext reads state]
    B --> F
    D --> F
    F --> G[CanvasRenderer draw call]
    G --> H[p5_canvas Rust renderer]
```

## Public API Call Flow

Global-mode functions are thin wrappers around the active context. A call such
as `p5.circle(100, 100, 40)` follows this path:

```mermaid
sequenceDiagram
    participant User as User sketch
    participant API as p5.api.global_mode
    participant Current as p5.api.current
    participant Ctx as SketchContext
    participant Renderer as CanvasRenderer
    participant Rust as p5_canvas

    User->>API: p5.circle(100, 100, 40)
    API->>Current: require_context()
    Current-->>API: active SketchContext
    API->>Ctx: circle(100, 100, 40)
    Ctx->>Ctx: read style, transform, color mode
    Ctx->>Renderer: ellipse/circle draw request
    Renderer->>Rust: bridge payload
```

This is why public API functions should stay small. If a function needs p5
semantics, validation, state changes, or renderer calls, that logic usually
belongs on `SketchContext`.

## Where To Make A Change

Use these rules of thumb:

- Add or expose a public function in `src/p5/api/global_mode.py` and
  `src/p5/__init__.py`.
- Implement sketch behavior in `SketchContext` when it depends on current p5
  state.
- Add persistent current values to `SketchState` when they must survive across
  API calls or frames.
- Add one-frame temporary values to `SketchContext` when they are not part of
  the public p5 state model.
- Change `CanvasRenderer` when the Python side already knows what should be
  drawn and only needs to translate the request for Rust.
- Change `CanvasBackend` when the behavior is about windows, scheduling,
  headless vs interactive mode, event polling, or shutdown.
- Change `p5.rust.canvas` when import/capability errors need to be clearer.
- Change `crates/p5_canvas` when the renderer/runtime itself lacks a primitive,
  export behavior, asset operation, or native event behavior.

## Source Map

- `src/p5/api/`: global-mode APIs and compatibility stubs.
- `src/p5/sketch.py`: sketch lifecycle and callback dispatch.
- `src/p5/context.py`: mutable sketch state and high-level drawing behavior.
- `src/p5/backends/`: runtime and renderer adapters.
- `src/p5/rust/`: Python wrappers around PyO3 extensions.
- `crates/p5_canvas/`: required canvas runtime.
- `crates/p5_accel/`: optional acceleration extension.

## Public API Rule

Canonical public functions use `snake_case`. Do not add camelCase aliases for
p5.js names. Unsupported browser-only APIs should raise explicit p5 exceptions,
usually `UnsupportedFeatureError` or `BackendCapabilityError`.

## Common Invariants

- A public drawing call must have an active `SketchContext`.
- `create_canvas()` must keep `SketchState.canvas` synchronized with the
  renderer's logical and physical dimensions.
- `push()` / `pop()` should preserve style and transform state together.
- Headless rendering must still go through `p5_canvas`.
- The public API should not expose `p5.rust._canvas` types directly.
- Missing backend capabilities should fail with package-specific errors, not
  raw import errors or renderer exceptions.
