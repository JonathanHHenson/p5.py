# Images, Pixels, and Assets

## Images

- `load_image(path)`
- `create_image(width, height)`
- `image(img, x, y, width=None, height=None, ...)`
- `image_mode(mode)`
- `image_sampling(mode)`

Images are loaded by the Rust canvas runtime. There is no Pillow fallback.

## Pixels

- `load_pixels()`
- `update_pixels()`
- `pixels()`
- `pixel_array()`
- `get(...)`
- `set(...)`

Pixel buffers are physical RGBA buffers. When `pixel_density()` is greater than
`1`, the physical pixel size is larger than the logical canvas size.

## Export

- `save_canvas(path=None)`
- `save_bytes(data, path)`
- `save_json(data, path)`
- `save_strings(lines, path)`
- `create_writer(path)`

## Data and Text Assets

- `load_json(path)`
- `load_strings(path)`
- `load_bytes(path)`
- `load_font(path)`

## Sound and Media

- `load_sound(path)`
- `create_audio(...)`
- `create_capture(...)`

Some media helpers require installing the `media` extra.

