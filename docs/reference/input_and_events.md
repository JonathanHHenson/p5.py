# Input and Events

Interactive input is available when the installed canvas extension supports a
native window.

## State Functions

- `mouse_x()`
- `mouse_y()`
- `pmouse_x()`
- `pmouse_y()`
- `moved_x()`
- `moved_y()`
- `mouse_is_pressed()`
- `mouse_button()`
- `key()`
- `key_code()`
- `key_is_pressed()`
- `key_is_down(code)`
- `touches()`
- `focused()`

## Callback Names

Define callbacks on a function-mode sketch module or on a `Sketch` subclass:

- `mouse_moved(event)`
- `mouse_dragged(event)`
- `mouse_pressed(event)`
- `mouse_released(event)`
- `mouse_clicked(event)`
- `mouse_double_clicked(event)`
- `mouse_wheel(event)`
- `key_pressed(event)`
- `key_released(event)`
- `key_typed(event)`
- `touch_started(event)`
- `touch_moved(event)`
- `touch_ended(event)`
- `touch_cancelled(event)`

Callbacks may also be declared without an event parameter.

