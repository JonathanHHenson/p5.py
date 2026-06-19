# Images, Pixels, and Assets

## Images

- `load_image(path)`
- `load_image_async(path)`
- `create_image(width, height)`
- `image(img, x, y, width=None, height=None, ...)`
- `image_mode(mode)`
- `image_sampling(mode)`

Images are loaded by the Rust canvas runtime. There is no Pillow fallback.
Async loader variants are awaitable and useful from `async def preload()` or
`async def setup()` callbacks.

Image objects also support Python indexing:

```python
color = img[x, y]
img[x, y] = p5.Color(255, 0, 0)
tile = img[x0:x1, y0:y1]
```

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
- `load_json_async(path)`
- `load_strings(path)`
- `load_strings_async(path)`
- `load_bytes(path)`
- `load_bytes_async(path)`
- `load_font(path)`
- `load_font_async(path)`

## Sound and Media

- `load_sound(path)`
- `load_sound_async(path)`
- `create_audio(...)`
- `create_capture(...)`
- `create_capture_async(...)`
- `create_video(...)`
- `create_video_async(...)`

Some media helpers require installing the `media` extra.

3D asset helpers also include awaitable variants:

- `load_model_async(path, normalize=False, package=None)`
- `load_shader_async(vertex_path, fragment_path)`
