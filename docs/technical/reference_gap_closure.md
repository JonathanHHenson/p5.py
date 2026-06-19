# p5.js beta reference gap closure

This note summarizes a compatibility review against the beta p5.js reference at <https://beta.p5js.org/reference/>. It is intentionally scoped to `p5-py` and the native Python runtime. The sibling `p5.js` repository was not analyzed here because this project should not depend on JavaScript, HTML, DOM APIs, or browser runtime details.

Epic 140 in `backlog/140_reference_gap_closure/` tracks the follow-up work.

## Compatibility policy

Every p5.js reference item should be classified as one of:

- `supported`: implemented and exported by p5-py.
- `partial`: implemented for a meaningful subset, with documented limitations.
- `pythonic_equivalent`: available through a Python-native API rather than a direct p5.js name.
- `deferred`: in scope someday, but blocked by renderer, media, platform, or design work.
- `excluded`: intentionally not part of p5-py.
- `not_applicable`: reference/tutorial/foundation material rather than a library API.

Canonical p5-py APIs are `snake_case` only. p5.js-style camelCase aliases should not be exported; sketch portability work should document the snake_case replacement instead.

## Current strong coverage

The current public API already covers substantial non-browser sketching:

- Sketch lifecycle and global mode: `run`, `setup`/`draw` discovery, `loop`, `no_loop`, `redraw`, `is_looping`, frame count, delta time, frame rate, and `millis`.
- Canvas/runtime basics: `create_canvas`, `resize_canvas`, width/height accessors, display/pixel density, headless/offscreen behavior through the canvas runtime.
- 2D primitives: `point`, `line`, `rect`, `square`, `ellipse`, `circle`, `triangle`, `quad`, `arc`.
- Core style and transform: fill/stroke state, stroke weight/cap/join, rect/ellipse/image modes, smoothing, push/pop, translate/rotate/scale/shear/apply/reset matrix, angle modes.
- Basic custom shapes and curves: `begin_shape`, `vertex`, `bezier_vertex`, `quadratic_vertex`, `end_shape`, `bezier`, `bezier_point`, and `bezier_tangent`.
- Color creation and interpolation: `color`, `color_mode`, `lerp_color`, plus RGB/HSB/HSL model support.
- Math/random/noise/vector basics: trigonometry, mapping/constrain/norm/lerp/dist/mag, seedable random/Gaussian/noise, and mutable vectors.
- Images/text/pixels: image loading/drawing/mode, font loading, text drawing and basic metrics, `load_pixels`, `update_pixels`, pixel array access, `blend`, `blend_mode`, `erase`, and `save_canvas`.
- Input basics: mouse position/movement/buttons, keyboard state, key lookup, and touch list support.
- Partial advanced media/3D: software/native canvas 3D slice for cameras, projection, orbit control, selected lights/materials, `plane`, `box`, `sphere`, model loading/drawing, shaders on supported native paths, file-backed sound, video, and capture.

## Major missing or partial feature groups

### Core 2D reference gaps

The high-value non-browser 2D gaps are mostly additive APIs on top of existing renderer/state foundations:

- Spline and custom shape parity: `spline`, `spline_point`, `spline_tangent`, `spline_vertex`, `spline_properties`, `spline_property`, `begin_contour`, `end_contour`, `bezier_order`, `normal`, and `vertex_property`.
- Color readers/mutators: `red`, `green`, `blue`, `alpha`, `hue`, `saturation`, `brightness`, `lightness`, `palette_lerp`, plus `Color` methods such as contrast, channel setters, alpha setter, and string formatting.
- Clipping/tinting: `begin_clip`, `clip`, `end_clip`, `tint`, and `no_tint` need native canvas semantics.
- Image/canvas pixel helpers: canvas-level `get`, `set`, `copy`, `filter`, `create_image`, `save_frames`, `save_gif`, and fuller `Image` method parity including animated GIF controls where feasible.
- Typography: font ascent/descent/width/bounds helpers, `text_bounds`, `text_direction`, `text_wrap`, `text_weight`, `text_properties`, and `text_property`.
- Offscreen rendering: `create_graphics`, framebuffer-like equivalents, `no_canvas`, and any `drawing_context` substitute need explicit canvas-runtime design before implementation.

### Math, data, and environment gaps

Many missing APIs are small compatibility utilities. They should be added only where they reduce porting friction without confusing Python users:

- Calculation helpers: p5-style names for `abs`, `ceil`, `exp`, `floor`, `log`, `pow`, `round`, `sqrt`, and careful treatment of `min`, `max`, and `map` because they overlap Python built-ins.
- Vector parity: indexed accessors, modulo/remainder, equality, clamp-to-zero, spherical interpolation, random 2D/3D constructors, angle constructors, reflection, and string formatting details.
- Quaternion helpers: axis-angle construction, multiplication, and rotation application, primarily if needed by 3D camera/model workflows.
- Data conversion/formatting: `boolean`, `byte`, `char`, `float`, `hex`, `int`, `str`, `unchar`, `unhex`, `nf`, `nfc`, `nfp`, `nfs`, `shuffle`, and `split_tokens`.
- Time/date/environment: `day`, `month`, `year`, `hour`, `minute`, `second`, `get_target_frame_rate`, `window_width`, `window_height`, display dimensions, focus state, cursor/no_cursor, and native behavior for `print`.
- Browser URL and localStorage helpers should not silently emulate browser state. They should be excluded or mapped to explicit Python-native alternatives with clear documentation.

### Events, accessibility, and IO gaps

Current mouse/keyboard/touch support is partial. The beta reference includes browser/device APIs that need careful classification:

- Pointer/keyboard callbacks and variables: `mouse_clicked`, `double_clicked`, `mouse_dragged`, `mouse_moved`, `mouse_released`, `mouse_wheel`, `key_pressed`, `key_released`, `key_typed`, `win_mouse_x/y`, previous window mouse values, and `code` semantics.
- Pointer lock is browser-specific and should remain excluded unless the native window runtime offers an explicit equivalent.
- Device acceleration/orientation APIs should remain deferred or excluded until a native sensor provider is selected.
- Accessibility helpers such as `describe`, `describe_element`, `grid_output`, and `text_output` produce browser screen-reader output in p5.js. A native Python equivalent would need a separate design, likely metadata/test hooks rather than DOM output.
- IO helpers should focus on local file workflows such as text, bytes, JSON, and writer-style output. Browser Blob/client-side save behavior is not a native Python concept.

### Advanced 3D, shaders, and WebGPU gaps

The 3D/media work is intentionally partial. Missing beta-reference areas should be separated into practical native milestones:

- 3D primitives and geometry: `cone`, `cylinder`, `ellipsoid`, `torus`, `build_geometry`, `create_model`, `save_obj`, `save_stl`, `free_geometry`, and p5.Geometry-style methods/properties.
- Camera/projection/interaction: `frustum`, `set_camera`, `roll`, debug grid/axes helpers, line perspective, and screen/world coordinate conversion.
- Lights/materials: `lights`, `no_lights`, `spot_light`, `image_light`, `panorama`, `light_falloff`, `specular_color`, `emissive_material`, `metalness`, `texture_mode`, and `texture_wrap`.
- Shader object parity: hook modification/inspection and context-copy APIs do not map directly to the current native shader design and should be explicitly classified.
- WebGPU, p5.strands, storage buffers, and compute shaders should remain deferred or excluded unless the Rust canvas runtime grows a native GPU abstraction that can support them safely.

## Explicit exclusions and non-goals

These remain intentionally out of scope unless the project policy changes:

- JavaScript, HTML, DOM APIs, and browser elements.
- `p5.XML`.
- `p5.Table` and `p5.TableRow`.
- Browser-only URL, localStorage, pointer-lock, and client-side-save semantics unless a native design is explicitly accepted.
- Foundation reference pages such as JavaScript `class`, `for`, `function`, `if`, `let`, and JavaScript primitive types. These are educational reference material, not p5-py API targets.

## Epic 140 breakdown

Epic 140 is split into focused PBIs:

- `reference_gap_audit.toml`: create the durable compatibility inventory and validation checks, including snake_case-only export checks.
- `core_2d_reference_parity.toml`: close high-value 2D/color/text/image/transform gaps.
- `math_data_environment_parity.toml`: add small math, data, time/date, and environment helpers.
- `events_accessibility_io_parity.toml`: clarify native event, accessibility, and IO behavior.
- `advanced_3d_webgpu_reference_gaps.toml`: classify advanced 3D, shader, geometry, WebGPU, and compute gaps.
