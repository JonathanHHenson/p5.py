# Canvas and Drawing

## Background and Clearing

- `background(*color)`
- `clear()`

## 2D Primitives

- `point(x, y)`
- `line(x1, y1, x2, y2)`
- `rect(x, y, width, height=None)`
- `square(x, y, size)`
- `ellipse(x, y, width, height=None)`
- `circle(x, y, diameter)`
- `triangle(x1, y1, x2, y2, x3, y3)`
- `quad(x1, y1, x2, y2, x3, y3, x4, y4)`
- `arc(...)`

## Paths and Curves

- `begin_shape(kind=None)`
- `vertex(x, y)`
- `bezier_vertex(...)`
- `quadratic_vertex(...)`
- `spline_vertex(...)`
- `end_shape(mode=None)`
- `bezier_point(...)`
- `bezier_tangent(...)`
- `spline_point(...)`
- `spline_tangent(...)`

## Images and Regions

- `image(img, x, y, width=None, height=None, ...)`
- `copy(...)`
- `get(...)`
- `set(...)`

## Compositing

- `blend_mode(mode)`
- `blend(...)`
- `erase(alpha=255, detail_alpha=255)`
- `no_erase()`
- `filter(kind, value=None)`

