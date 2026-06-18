mod gpu;
mod runtime;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use runtime::{
    native_window_available as runtime_native_window_available, InteractiveRuntime, RuntimeEvent,
};
use std::collections::HashMap;
use std::f64::consts::PI;

const SUPPORTED_RENDERER: &str = "p2d";
const SUPPORTED_MODE: &str = "headless";
const INTERACTIVE_MODE: &str = "interactive";
const BLEND_MODE_BLEND: &str = "blend";
const BLEND_MODE_ADD: &str = "add";
const BLEND_MODE_DARKEST: &str = "darkest";
const BLEND_MODE_LIGHTEST: &str = "lightest";
const BLEND_MODE_DIFFERENCE: &str = "difference";
const BLEND_MODE_EXCLUSION: &str = "exclusion";
const BLEND_MODE_MULTIPLY: &str = "multiply";
const BLEND_MODE_REPLACE: &str = "replace";
const BLEND_MODE_SCREEN: &str = "screen";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Rgba {
    r: u8,
    g: u8,
    b: u8,
    a: u8,
}

impl Rgba {
    fn from_tuple(tuple: (u8, u8, u8, u8)) -> Self {
        Self {
            r: tuple.0,
            g: tuple.1,
            b: tuple.2,
            a: tuple.3,
        }
    }

    fn as_array(self) -> [u8; 4] {
        [self.r, self.g, self.b, self.a]
    }
}

#[derive(Clone, Debug)]
struct Style {
    fill: Option<Rgba>,
    stroke: Option<Rgba>,
    stroke_weight: f64,
    blend_mode: String,
    erasing: bool,
    image_sampling: String,
}

#[derive(Clone, Debug)]
struct CachedImage {
    version: u64,
    width: usize,
    height: usize,
    pixels: Vec<u8>,
}

type Matrix = (f64, f64, f64, f64, f64, f64);

type Point = (f64, f64);

struct OverlayRegion<'a> {
    min_x: usize,
    min_y: usize,
    width: usize,
    height: usize,
    canvas_width: usize,
    pixels: &'a mut [u8],
    present_pixels: &'a mut [u32],
    erasing: bool,
    blend_mode: &'a str,
}

impl<'a> OverlayRegion<'a> {
    fn from_bounds(
        bounds: (usize, usize, usize, usize),
        canvas_width: usize,
        pixels: &'a mut [u8],
        present_pixels: &'a mut [u32],
        erasing: bool,
        blend_mode: &'a str,
    ) -> Option<Self> {
        let (min_x, min_y, max_x, max_y) = bounds;
        let width = max_x.saturating_sub(min_x);
        let height = max_y.saturating_sub(min_y);
        if width == 0 || height == 0 {
            return None;
        }
        Some(Self {
            min_x,
            min_y,
            width,
            height,
            canvas_width,
            pixels,
            present_pixels,
            erasing,
            blend_mode,
        })
    }

    fn max_x(&self) -> usize {
        self.min_x + self.width
    }

    fn max_y(&self) -> usize {
        self.min_y + self.height
    }

    fn set_pixel(&mut self, x: usize, y: usize, color: Rgba) {
        let pixel_index = y * self.canvas_width + x;
        let offset = pixel_index * 4;
        let dst = &mut self.pixels[offset..offset + 4];
        let color = color.as_array();
        if self.erasing {
            dst[3] = dst[3].saturating_sub(color[3]);
        } else {
            blend_pixel(dst, &color, self.blend_mode);
        }
        self.present_pixels[pixel_index] = rgba_to_present_pixel(dst);
    }
}

#[pyclass(unsendable)]
struct Canvas {
    width: i64,
    height: i64,
    physical_width: usize,
    physical_height: usize,
    pixel_density: f64,
    mode: String,
    window_open: bool,
    closed: bool,
    pixels: Vec<u8>,
    present_pixels: Vec<u32>,
    image_cache: HashMap<u64, CachedImage>,
    runtime: Option<InteractiveRuntime>,
    gpu: Option<gpu::GpuRenderer>,
    gpu_error: Option<String>,
    render_dirty: bool,
    offscreen_dirty: bool,
    pixels_stale: bool,
    texture_stale: bool,
}

#[pymethods]
impl Canvas {
    #[new]
    #[pyo3(signature = (width, height, pixel_density=1.0, mode=SUPPORTED_MODE, renderer=SUPPORTED_RENDERER))]
    fn new(
        width: i64,
        height: i64,
        pixel_density: f64,
        mode: &str,
        renderer: &str,
    ) -> PyResult<Self> {
        validate_mode_and_renderer(mode, renderer)?;
        let (physical_width, physical_height) = physical_dimensions(width, height, pixel_density)?;
        let (gpu, gpu_error) = match gpu::GpuRenderer::new(physical_width, physical_height) {
            Ok(renderer) => (Some(renderer), None),
            Err(err) => (None, Some(err)),
        };
        Ok(Self {
            width,
            height,
            physical_width,
            physical_height,
            pixel_density,
            mode: mode.to_string(),
            window_open: mode == INTERACTIVE_MODE,
            closed: false,
            pixels: vec![0; physical_width * physical_height * 4],
            present_pixels: vec![0; physical_width * physical_height],
            image_cache: HashMap::new(),
            runtime: None,
            gpu,
            gpu_error,
            render_dirty: false,
            offscreen_dirty: false,
            pixels_stale: false,
            texture_stale: false,
        })
    }

    fn resize(
        &mut self,
        width: i64,
        height: i64,
        pixel_density: f64,
        renderer: &str,
    ) -> PyResult<()> {
        validate_renderer(renderer)?;
        let (physical_width, physical_height) = physical_dimensions(width, height, pixel_density)?;
        self.width = width;
        self.height = height;
        self.pixel_density = pixel_density;
        self.physical_width = physical_width;
        self.physical_height = physical_height;
        self.pixels = vec![0; physical_width * physical_height * 4];
        self.present_pixels = vec![0; physical_width * physical_height];
        if let Some(gpu) = self.gpu.as_mut() {
            gpu.resize(physical_width, physical_height);
            gpu.clear_transparent();
            gpu.render();
        }
        self.render_dirty = false;
        self.offscreen_dirty = false;
        self.pixels_stale = false;
        self.texture_stale = false;
        if let Some(runtime) = self.runtime.as_mut() {
            runtime
                .request_resize(width, height, pixel_density)
                .map_err(|err| {
                    PyValueError::new_err(format!("Failed to resize native canvas window: {err}"))
                })?;
        }
        Ok(())
    }

    fn dimensions(&self) -> (i64, i64, usize, usize, f64) {
        (
            self.width,
            self.height,
            self.physical_width,
            self.physical_height,
            self.pixel_density,
        )
    }

    fn display_density(&self) -> f64 {
        if let Some(runtime) = self.runtime.as_ref() {
            runtime.display_density()
        } else if self.window_open {
            self.pixel_density.max(1.0)
        } else {
            1.0
        }
    }

    fn native_window_available(&self) -> bool {
        runtime_native_window_available()
    }

    fn gpu_available(&self) -> bool {
        self.gpu.is_some()
    }

    fn gpu_status(&self) -> String {
        self.gpu_error
            .clone()
            .unwrap_or_else(|| "available".to_string())
    }

    fn open_window(&mut self) -> PyResult<()> {
        self.mode = INTERACTIVE_MODE.to_string();
        self.window_open = true;
        self.closed = false;
        self.runtime = Some(
            InteractiveRuntime::open(self.width, self.height).map_err(|err| {
                PyValueError::new_err(format!("Failed to open native canvas window: {err}"))
            })?,
        );
        Ok(())
    }

    fn should_close(&self) -> bool {
        self.closed
            || self
                .runtime
                .as_ref()
                .map(|runtime| runtime.should_close())
                .unwrap_or(false)
    }

    fn poll_events(&mut self) -> PyResult<Vec<Py<PyAny>>> {
        let Some(runtime) = self.runtime.as_mut() else {
            return Ok(Vec::new());
        };
        let events = runtime.poll_events().map_err(|err| {
            PyValueError::new_err(format!("Failed to poll native canvas events: {err}"))
        })?;
        if runtime.should_close() {
            self.closed = true;
        }
        Python::with_gil(|py| {
            events
                .into_iter()
                .map(|event| runtime_event_to_pyobject(py, event))
                .collect()
        })
    }

    fn begin_frame(&mut self) {
        if let Some(gpu) = self.gpu.as_mut() {
            gpu.begin_frame();
        }
        self.render_dirty = false;
    }

    fn end_frame(&mut self) {
        if self.render_dirty && self.offscreen_dirty && self.runtime.is_none() {
            self.render_gpu_frame(false);
        } else if self.runtime.is_none() {
            self.render_dirty = false;
        }
    }

    fn present(&mut self) -> PyResult<()> {
        if self.render_dirty && self.offscreen_dirty && self.runtime.is_none() {
            self.render_gpu_frame(false);
        } else if self.runtime.is_none() {
            self.render_dirty = false;
        }
        if self.runtime.is_some() && self.render_dirty {
            self.upload_stale_texture(false)?;
        }
        if let Some(runtime) = self.runtime.as_mut() {
            let window = runtime.window().ok_or_else(|| {
                PyValueError::new_err("Native canvas window is not available for presentation.")
            })?;
            let (surface_width, surface_height) = runtime.physical_size();
            let gpu = self.gpu.as_mut().ok_or_else(|| {
                PyValueError::new_err(
                    self.gpu_error
                        .clone()
                        .unwrap_or_else(|| "GPU presentation is unavailable.".to_string()),
                )
            })?;
            if self.render_dirty {
                if self.offscreen_dirty {
                    gpu.render();
                    gpu.begin_frame();
                    self.offscreen_dirty = false;
                    self.pixels_stale = true;
                    self.texture_stale = false;
                }
                gpu.present_texture_to_window(window, surface_width, surface_height)
                    .map_err(|err| {
                        PyValueError::new_err(format!("Failed to present native GPU frame: {err}"))
                    })?;
                self.render_dirty = false;
            }
            if runtime.should_close() {
                self.closed = true;
            }
        }
        Ok(())
    }

    fn close(&mut self) {
        self.closed = true;
        if let Some(runtime) = self.runtime.as_mut() {
            runtime.close();
        }
        if let Some(gpu) = self.gpu.as_mut() {
            gpu.drop_surface();
        }
        self.runtime = None;
    }

    fn background(&mut self, rgba: (u8, u8, u8, u8)) {
        let color = Rgba::from_tuple(rgba).as_array();
        if let Some(gpu) = self.gpu.as_mut() {
            gpu.set_clear_color(gpu_color(Rgba::from_tuple(rgba)));
            self.render_dirty = true;
            self.offscreen_dirty = true;
            self.pixels_stale = true;
        } else {
            let packed = rgba_to_present_pixel(&color);
            fill_rgba_buffer(&mut self.pixels, &color);
            self.present_pixels.fill(packed);
        }
    }

    fn clear(&mut self) {
        if let Some(gpu) = self.gpu.as_mut() {
            gpu.clear_transparent();
            self.render_dirty = true;
            self.offscreen_dirty = true;
            self.pixels_stale = true;
        } else {
            self.pixels.fill(0);
            self.present_pixels.fill(0);
        }
    }

    fn point(&mut self, x: f64, y: f64, style: &Bound<'_, PyAny>, matrix: Matrix) -> PyResult<()> {
        let style = parse_style(style)?;
        ensure_supported_style(&style)?;
        let color = match style.stroke.or(style.fill) {
            Some(color) => color,
            None => return Ok(()),
        };
        let (tx, ty) = self.transform_point(matrix, x, y);
        let radius = (style.stroke_weight * self.pixel_density / 2.0).max(0.5);
        let bounds = clipped_bounds(
            &[(tx, ty)],
            radius,
            self.physical_width,
            self.physical_height,
        );
        if self.can_queue_gpu_primitives(&style) {
            self.draw_gpu_disc(tx, ty, radius, color);
            return Ok(());
        }
        self.prepare_cpu_composite();
        let Some(mut overlay) = OverlayRegion::from_bounds(
            bounds,
            self.physical_width,
            &mut self.pixels,
            &mut self.present_pixels,
            style.erasing,
            &style.blend_mode,
        ) else {
            return Ok(());
        };
        fill_disc(&mut overlay, tx, ty, radius, color);
        self.upload_cpu_pixels()?;
        Ok(())
    }

    fn line(
        &mut self,
        x1: f64,
        y1: f64,
        x2: f64,
        y2: f64,
        style: &Bound<'_, PyAny>,
        matrix: Matrix,
    ) -> PyResult<()> {
        let style = parse_style(style)?;
        ensure_supported_style(&style)?;
        let stroke = match style.stroke {
            Some(color) => color,
            None => return Ok(()),
        };
        let p1 = self.transform_point(matrix, x1, y1);
        let p2 = self.transform_point(matrix, x2, y2);
        let radius = stroke_width(style.stroke_weight, self.pixel_density) / 2.0;
        let bounds = clipped_bounds(&[p1, p2], radius, self.physical_width, self.physical_height);
        if self.can_queue_gpu_primitives(&style) {
            self.draw_gpu_segment(p1, p2, radius * 2.0, stroke);
            return Ok(());
        }
        self.prepare_cpu_composite();
        let Some(mut overlay) = OverlayRegion::from_bounds(
            bounds,
            self.physical_width,
            &mut self.pixels,
            &mut self.present_pixels,
            style.erasing,
            &style.blend_mode,
        ) else {
            return Ok(());
        };
        stroke_segment(&mut overlay, p1, p2, radius * 2.0, stroke);
        self.upload_cpu_pixels()?;
        Ok(())
    }

    #[pyo3(signature = (points, style, matrix, close=true))]
    fn polygon(
        &mut self,
        points: Vec<(f64, f64)>,
        style: &Bound<'_, PyAny>,
        matrix: Matrix,
        close: bool,
    ) -> PyResult<()> {
        let style = parse_style(style)?;
        ensure_supported_style(&style)?;
        if points.is_empty() {
            return Ok(());
        }
        let transformed: Vec<Point> = points
            .iter()
            .map(|(x, y)| self.transform_point(matrix, *x, *y))
            .collect();
        let padding = if style.stroke.is_some() {
            stroke_width(style.stroke_weight, self.pixel_density) / 2.0
        } else {
            0.0
        };
        let bounds = clipped_bounds(
            &transformed,
            padding,
            self.physical_width,
            self.physical_height,
        );
        if self.can_queue_gpu_primitives(&style) {
            self.draw_gpu_polygon(&transformed, &style, close, self.pixel_density);
            return Ok(());
        }
        self.prepare_cpu_composite();
        let Some(mut overlay) = OverlayRegion::from_bounds(
            bounds,
            self.physical_width,
            &mut self.pixels,
            &mut self.present_pixels,
            style.erasing,
            &style.blend_mode,
        ) else {
            return Ok(());
        };
        draw_polygon_overlay(
            &mut overlay,
            &transformed,
            &style,
            close,
            self.pixel_density,
        );
        self.upload_cpu_pixels()?;
        Ok(())
    }

    fn ellipse(
        &mut self,
        x: f64,
        y: f64,
        width: f64,
        height: f64,
        style: &Bound<'_, PyAny>,
        matrix: Matrix,
    ) -> PyResult<()> {
        let parsed_style = parse_style(style)?;
        ensure_supported_style(&parsed_style)?;
        if let Some((cx, cy, rx, ry)) =
            self.axis_aligned_ellipse_geometry(matrix, x, y, width, height)
        {
            let padding = if parsed_style.stroke.is_some() {
                stroke_width(parsed_style.stroke_weight, self.pixel_density) / 2.0
            } else {
                0.0
            };
            let bounds = ellipse_bounds(
                cx,
                cy,
                rx,
                ry,
                padding,
                self.physical_width,
                self.physical_height,
            );
            if self.can_queue_gpu_primitives(&parsed_style) {
                self.draw_gpu_axis_aligned_ellipse(
                    cx,
                    cy,
                    rx,
                    ry,
                    &parsed_style,
                    self.pixel_density,
                );
                return Ok(());
            }
            self.prepare_cpu_composite();
            let Some(mut overlay) = OverlayRegion::from_bounds(
                bounds,
                self.physical_width,
                &mut self.pixels,
                &mut self.present_pixels,
                parsed_style.erasing,
                &parsed_style.blend_mode,
            ) else {
                return Ok(());
            };
            draw_axis_aligned_ellipse(
                &mut overlay,
                cx,
                cy,
                rx,
                ry,
                &parsed_style,
                self.pixel_density,
            );
            self.upload_cpu_pixels()?;
            return Ok(());
        }

        let cx = x + width / 2.0;
        let cy = y + height / 2.0;
        let rx = width / 2.0;
        let ry = height / 2.0;
        let points: Vec<Point> = (0..64)
            .map(|index| {
                let t = 2.0 * PI * index as f64 / 64.0;
                (cx + t.cos() * rx, cy + t.sin() * ry)
            })
            .collect();
        self.polygon(points, style, matrix, true)
    }

    fn arc(
        &mut self,
        x: f64,
        y: f64,
        width: f64,
        height: f64,
        start: f64,
        mut stop: f64,
        mode: &str,
        style: &Bound<'_, PyAny>,
        matrix: Matrix,
    ) -> PyResult<()> {
        let cx = x + width / 2.0;
        let cy = y + height / 2.0;
        let rx = width / 2.0;
        let ry = height / 2.0;
        while stop < start {
            stop += 2.0 * PI;
        }
        let steps = ((stop - start).abs() / (2.0 * PI) * 64.0).floor().max(8.0) as usize;
        let arc_points: Vec<Point> = (0..=steps)
            .map(|index| {
                let t = start + (stop - start) * index as f64 / steps as f64;
                (cx + t.cos() * rx, cy + t.sin() * ry)
            })
            .collect();
        match mode {
            "pie" => {
                let mut points = vec![(cx, cy)];
                points.extend(arc_points);
                self.polygon(points, style, matrix, true)
            }
            "chord" => self.polygon(arc_points, style, matrix, true),
            _ => {
                let parsed_style = parse_style(style)?;
                ensure_supported_style(&parsed_style)?;
                let transformed: Vec<Point> = arc_points
                    .iter()
                    .map(|(px, py)| self.transform_point(matrix, *px, *py))
                    .collect();
                let padding = if parsed_style.stroke.is_some() {
                    stroke_width(parsed_style.stroke_weight, self.pixel_density) / 2.0
                } else {
                    0.0
                };
                let bounds = clipped_bounds(
                    &transformed,
                    padding,
                    self.physical_width,
                    self.physical_height,
                );
                if self.can_queue_gpu_primitives(&parsed_style) {
                    if parsed_style.fill.is_some() && mode != "open" {
                        self.draw_gpu_polygon(
                            &transformed,
                            &Style {
                                stroke: None,
                                ..parsed_style.clone()
                            },
                            true,
                            self.pixel_density,
                        );
                    }
                    if let Some(stroke) = parsed_style.stroke {
                        self.draw_gpu_polyline(
                            &transformed,
                            false,
                            stroke_width(parsed_style.stroke_weight, self.pixel_density),
                            stroke,
                        );
                    }
                    return Ok(());
                }
                self.prepare_cpu_composite();
                let Some(mut overlay) = OverlayRegion::from_bounds(
                    bounds,
                    self.physical_width,
                    &mut self.pixels,
                    &mut self.present_pixels,
                    parsed_style.erasing,
                    &parsed_style.blend_mode,
                ) else {
                    return Ok(());
                };
                if parsed_style.fill.is_some() && mode != "open" {
                    draw_polygon_overlay(
                        &mut overlay,
                        &transformed,
                        &Style {
                            stroke: None,
                            ..parsed_style.clone()
                        },
                        true,
                        self.pixel_density,
                    );
                }
                if let Some(stroke) = parsed_style.stroke {
                    draw_polyline_stroke(
                        &mut overlay,
                        &transformed,
                        false,
                        stroke_width(parsed_style.stroke_weight, self.pixel_density),
                        stroke,
                    );
                }
                self.upload_cpu_pixels()?;
                Ok(())
            }
        }
    }

    #[pyo3(signature = (image_pixels, image_width, image_height, dx, dy, dw, dh, style, matrix, source=None))]
    fn draw_image(
        &mut self,
        image_pixels: Vec<u8>,
        image_width: usize,
        image_height: usize,
        dx: f64,
        dy: f64,
        dw: f64,
        dh: f64,
        style: &Bound<'_, PyAny>,
        matrix: Matrix,
        source: Option<(i64, i64, i64, i64)>,
    ) -> PyResult<()> {
        self.draw_image_pixels(
            &image_pixels,
            image_width,
            image_height,
            dx,
            dy,
            dw,
            dh,
            style,
            matrix,
            source,
        )
    }

    #[pyo3(signature = (image_key, image_version, image_pixels, image_width, image_height, dx, dy, dw, dh, style, matrix, source=None))]
    fn draw_cached_image(
        &mut self,
        image_key: u64,
        image_version: u64,
        image_pixels: Option<Vec<u8>>,
        image_width: usize,
        image_height: usize,
        dx: f64,
        dy: f64,
        dw: f64,
        dh: f64,
        style: &Bound<'_, PyAny>,
        matrix: Matrix,
        source: Option<(i64, i64, i64, i64)>,
    ) -> PyResult<()> {
        let needs_upload = self
            .image_cache
            .get(&image_key)
            .map(|cached| {
                cached.version != image_version
                    || cached.width != image_width
                    || cached.height != image_height
            })
            .unwrap_or(true);
        if needs_upload {
            let pixels = image_pixels.ok_or_else(|| {
                PyValueError::new_err(
                    "Image pixels are required the first time an image/version is drawn.",
                )
            })?;
            validate_rgba_buffer(pixels.len(), image_width, image_height)?;
            self.image_cache.insert(
                image_key,
                CachedImage {
                    version: image_version,
                    width: image_width,
                    height: image_height,
                    pixels,
                },
            );
        }
        let cached = self
            .image_cache
            .get(&image_key)
            .ok_or_else(|| PyValueError::new_err("Cached image is not available."))?
            .clone();
        self.draw_image_pixels(
            &cached.pixels,
            cached.width,
            cached.height,
            dx,
            dy,
            dw,
            dh,
            style,
            matrix,
            source,
        )
    }

    #[pyo3(signature = (source_pixels, source_width, source_height, source, destination, mode))]
    fn blend_region(
        &mut self,
        source_pixels: Option<Vec<u8>>,
        source_width: Option<usize>,
        source_height: Option<usize>,
        source: (i64, i64, i64, i64),
        destination: (i64, i64, i64, i64),
        mode: &str,
    ) -> PyResult<()> {
        ensure_supported_blend_mode(mode)?;
        let (dest_x, dest_y, dest_w, dest_h) = scale_rect(destination, self.pixel_density);
        if dest_w <= 0 || dest_h <= 0 {
            return Ok(());
        }
        self.prepare_cpu_composite();
        let source_owned;
        let (source_data, source_canvas_width, source_canvas_height, source_rect) =
            if let Some(pixels) = source_pixels {
                let width = source_width.ok_or_else(|| {
                    PyValueError::new_err("External blend source width is required.")
                })?;
                let height = source_height.ok_or_else(|| {
                    PyValueError::new_err("External blend source height is required.")
                })?;
                validate_rgba_buffer(pixels.len(), width, height)?;
                source_owned = pixels;
                (&source_owned[..], width, height, source)
            } else {
                (
                    &self.pixels[..],
                    self.physical_width,
                    self.physical_height,
                    scale_rect(source, self.pixel_density),
                )
            };
        let Some((sx, sy, sw, sh)) =
            clipped_source_rect(source_rect, source_canvas_width, source_canvas_height)
        else {
            return Ok(());
        };
        let Some((dx, dy, dw, dh)) = clipped_dest_rect(
            (dest_x, dest_y, dest_w, dest_h),
            self.physical_width,
            self.physical_height,
        ) else {
            return Ok(());
        };
        let sampled = source_data.to_vec();
        blit_scaled_region(
            &mut self.pixels,
            &mut self.present_pixels,
            self.physical_width,
            &sampled,
            source_canvas_width,
            sx,
            sy,
            sw,
            sh,
            dx,
            dy,
            dw,
            dh,
            false,
            mode,
            "linear",
        );
        self.upload_cpu_pixels()?;
        Ok(())
    }

    fn load_pixels(&mut self) -> Vec<u8> {
        if self.offscreen_dirty && self.pixels_stale {
            self.render_gpu_frame(true);
        } else if self.pixels_stale {
            self.read_gpu_pixels();
        }
        self.pixels.clone()
    }

    fn update_pixels(&mut self, pixels: Vec<u8>) -> PyResult<()> {
        let expected = self.physical_width * self.physical_height * 4;
        if pixels.len() != expected {
            return Err(PyValueError::new_err(format!(
                "Pixel buffer length must be {expected}, got {}.",
                pixels.len()
            )));
        }
        self.pixels = pixels;
        self.sync_present_pixels_from_rgba();
        if let Some(gpu) = self.gpu.as_mut() {
            gpu.begin_frame();
        }
        self.render_dirty = true;
        self.offscreen_dirty = false;
        self.pixels_stale = false;
        self.texture_stale = true;
        Ok(())
    }

    fn save(&mut self, path: &str) -> PyResult<()> {
        if self.offscreen_dirty && self.pixels_stale {
            self.render_gpu_frame(true);
        } else if self.pixels_stale {
            self.read_gpu_pixels();
        }
        image::save_buffer_with_format(
            path,
            &self.pixels,
            self.physical_width as u32,
            self.physical_height as u32,
            image::ColorType::Rgba8,
            image::ImageFormat::Png,
        )
        .map_err(|err| PyValueError::new_err(format!("Failed to save canvas: {err}")))
    }
}

impl Canvas {
    #[allow(clippy::too_many_arguments)]
    fn draw_image_pixels(
        &mut self,
        image_pixels: &[u8],
        image_width: usize,
        image_height: usize,
        dx: f64,
        dy: f64,
        dw: f64,
        dh: f64,
        style: &Bound<'_, PyAny>,
        matrix: Matrix,
        source: Option<(i64, i64, i64, i64)>,
    ) -> PyResult<()> {
        let style = parse_style(style)?;
        ensure_supported_style(&style)?;
        if dw <= 0.0 || dh <= 0.0 || image_width == 0 || image_height == 0 {
            return Ok(());
        }
        validate_rgba_buffer(image_pixels.len(), image_width, image_height)?;
        let source = source.unwrap_or((0, 0, image_width as i64, image_height as i64));
        let Some((sx, sy, sw, sh)) = clipped_source_rect(source, image_width, image_height) else {
            return Ok(());
        };
        let image_to_canvas =
            image_to_canvas_matrix(matrix, dx, dy, dw, dh, sw, sh, self.pixel_density);
        if matrix_determinant(image_to_canvas).abs() <= f64::EPSILON {
            return Ok(());
        }
        if let Some((dest_x, dest_y, dest_w, dest_h)) = axis_aligned_image_destination(
            image_to_canvas,
            sw,
            sh,
            self.physical_width,
            self.physical_height,
        ) {
            self.prepare_cpu_composite();
            blit_scaled_region(
                &mut self.pixels,
                &mut self.present_pixels,
                self.physical_width,
                image_pixels,
                image_width,
                sx,
                sy,
                sw,
                sh,
                dest_x,
                dest_y,
                dest_w,
                dest_h,
                style.erasing,
                &style.blend_mode,
                &style.image_sampling,
            );
            self.upload_cpu_pixels()?;
            return Ok(());
        }
        let Some((dest_x, dest_y, dest_w, dest_h)) = affine_bounds(
            image_to_canvas,
            sw,
            sh,
            self.physical_width,
            self.physical_height,
        ) else {
            return Ok(());
        };
        let canvas_to_image = matrix_inverse(image_to_canvas).ok_or_else(|| {
            PyValueError::new_err("Image transform is not invertible for p5_canvas.")
        })?;
        self.prepare_cpu_composite();
        blit_affine_region(
            &mut self.pixels,
            &mut self.present_pixels,
            self.physical_width,
            image_pixels,
            image_width,
            sx,
            sy,
            sw,
            sh,
            dest_x,
            dest_y,
            dest_w,
            dest_h,
            canvas_to_image,
            style.erasing,
            &style.blend_mode,
            &style.image_sampling,
        );
        self.upload_cpu_pixels()?;
        Ok(())
    }

    fn transform_point(&self, matrix: Matrix, x: f64, y: f64) -> Point {
        let (a, b, c, d, e, f) = matrix;
        (
            (a * x + c * y + e) * self.pixel_density,
            (b * x + d * y + f) * self.pixel_density,
        )
    }

    fn axis_aligned_ellipse_geometry(
        &self,
        matrix: Matrix,
        x: f64,
        y: f64,
        width: f64,
        height: f64,
    ) -> Option<(f64, f64, f64, f64)> {
        let (a, b, c, d, e, f) = matrix;
        if b.abs() > f64::EPSILON || c.abs() > f64::EPSILON {
            return None;
        }
        let cx = x + width / 2.0;
        let cy = y + height / 2.0;
        Some((
            (a * cx + e) * self.pixel_density,
            (d * cy + f) * self.pixel_density,
            (width * a * self.pixel_density / 2.0).abs(),
            (height * d * self.pixel_density / 2.0).abs(),
        ))
    }

    fn sync_present_pixels_from_rgba(&mut self) {
        for (index, rgba) in self.pixels.chunks_exact(4).enumerate() {
            self.present_pixels[index] = rgba_to_present_pixel(rgba);
        }
    }

    fn can_queue_gpu_primitives(&self, style: &Style) -> bool {
        self.gpu.is_some() && !style.erasing && style.blend_mode == BLEND_MODE_BLEND
    }

    fn prepare_cpu_composite(&mut self) {
        if self.offscreen_dirty && self.pixels_stale {
            self.render_gpu_frame(true);
        } else if self.pixels_stale {
            self.read_gpu_pixels();
        }
    }

    fn upload_cpu_pixels(&mut self) -> PyResult<()> {
        if let Some(gpu) = self.gpu.as_mut() {
            gpu.begin_frame();
        }
        self.render_dirty = true;
        self.offscreen_dirty = false;
        self.pixels_stale = false;
        self.texture_stale = true;
        Ok(())
    }

    fn upload_stale_texture(&mut self, consume_mirrored_commands: bool) -> PyResult<()> {
        if !self.texture_stale {
            return Ok(());
        }
        if let Some(gpu) = self.gpu.as_mut() {
            gpu.upload_pixels(&self.pixels)
                .map_err(|err| PyValueError::new_err(format!("Failed to upload pixels: {err}")))?;
            if consume_mirrored_commands {
                gpu.begin_frame();
            }
        }
        self.texture_stale = false;
        if consume_mirrored_commands {
            self.offscreen_dirty = false;
            self.pixels_stale = false;
        }
        Ok(())
    }

    fn render_gpu_frame(&mut self, readback: bool) {
        if self.upload_stale_texture(false).is_err() {
            self.render_dirty = false;
            self.offscreen_dirty = false;
            self.texture_stale = false;
            return;
        }
        let Some(gpu) = self.gpu.as_mut() else {
            self.render_dirty = false;
            self.offscreen_dirty = false;
            self.texture_stale = false;
            return;
        };
        gpu.render();
        gpu.begin_frame();
        self.render_dirty = false;
        self.offscreen_dirty = false;
        self.pixels_stale = true;
        self.texture_stale = false;
        if readback {
            self.read_gpu_pixels();
        }
    }

    fn read_gpu_pixels(&mut self) {
        let Some(gpu) = self.gpu.as_ref() else {
            self.pixels_stale = false;
            return;
        };
        match gpu.read_pixels() {
            Ok(pixels) => {
                self.pixels = pixels;
                self.sync_present_pixels_from_rgba();
                self.pixels_stale = false;
            }
            Err(err) => {
                self.gpu_error = Some(err);
                self.pixels_stale = false;
            }
        }
    }

    fn draw_gpu_polygon(
        &mut self,
        points: &[Point],
        style: &Style,
        close: bool,
        pixel_density: f64,
    ) {
        if style.erasing {
            return;
        }
        if close && points.len() >= 3 {
            if let Some(fill) = style.fill {
                let mut vertices = Vec::with_capacity((points.len() - 2) * 3);
                for index in 1..points.len() - 1 {
                    push_triangle(
                        &mut vertices,
                        points[0],
                        points[index],
                        points[index + 1],
                        fill,
                    );
                }
                self.draw_gpu_triangles(vertices);
            }
        }
        if let Some(stroke) = style.stroke {
            self.draw_gpu_polyline(
                points,
                close,
                stroke_width(style.stroke_weight, pixel_density),
                stroke,
            );
        }
    }

    fn draw_gpu_polyline(&mut self, points: &[Point], close: bool, stroke_width: f64, color: Rgba) {
        if points.len() < 2 {
            return;
        }
        for pair in points.windows(2) {
            self.draw_gpu_segment(pair[0], pair[1], stroke_width, color);
        }
        if close {
            self.draw_gpu_segment(
                *points.last().expect("non-empty points"),
                points[0],
                stroke_width,
                color,
            );
        }
    }

    fn draw_gpu_segment(&mut self, p1: Point, p2: Point, stroke_width: f64, color: Rgba) {
        let dx = p2.0 - p1.0;
        let dy = p2.1 - p1.1;
        let length = (dx * dx + dy * dy).sqrt();
        if length <= f64::EPSILON {
            self.draw_gpu_disc(p1.0, p1.1, (stroke_width / 2.0).max(0.5), color);
            return;
        }
        let half = (stroke_width / 2.0).max(0.5);
        let nx = -dy / length * half;
        let ny = dx / length * half;
        let a = (p1.0 + nx, p1.1 + ny);
        let b = (p1.0 - nx, p1.1 - ny);
        let c = (p2.0 - nx, p2.1 - ny);
        let d = (p2.0 + nx, p2.1 + ny);
        let mut vertices = Vec::with_capacity(6);
        push_triangle(&mut vertices, a, b, c, color);
        push_triangle(&mut vertices, a, c, d, color);
        self.draw_gpu_triangles(vertices);
    }

    fn draw_gpu_disc(&mut self, cx: f64, cy: f64, radius: f64, color: Rgba) {
        if radius <= 0.0 {
            return;
        }
        let steps = 24usize;
        let mut vertices = Vec::with_capacity(steps * 3);
        for index in 0..steps {
            let a = 2.0 * PI * index as f64 / steps as f64;
            let b = 2.0 * PI * (index + 1) as f64 / steps as f64;
            push_triangle(
                &mut vertices,
                (cx, cy),
                (cx + a.cos() * radius, cy + a.sin() * radius),
                (cx + b.cos() * radius, cy + b.sin() * radius),
                color,
            );
        }
        self.draw_gpu_triangles(vertices);
    }

    fn draw_gpu_axis_aligned_ellipse(
        &mut self,
        cx: f64,
        cy: f64,
        rx: f64,
        ry: f64,
        style: &Style,
        pixel_density: f64,
    ) {
        if style.erasing || rx <= 0.0 || ry <= 0.0 {
            return;
        }
        if let Some(fill) = style.fill {
            let steps = 64usize;
            let mut vertices = Vec::with_capacity(steps * 3);
            for index in 0..steps {
                let a = 2.0 * PI * index as f64 / steps as f64;
                let b = 2.0 * PI * (index + 1) as f64 / steps as f64;
                push_triangle(
                    &mut vertices,
                    (cx, cy),
                    (cx + a.cos() * rx, cy + a.sin() * ry),
                    (cx + b.cos() * rx, cy + b.sin() * ry),
                    fill,
                );
            }
            self.draw_gpu_triangles(vertices);
        }
        if let Some(stroke) = style.stroke {
            let half_width = (stroke_width(style.stroke_weight, pixel_density) / 2.0).max(0.5);
            let outer_rx = rx + half_width;
            let outer_ry = ry + half_width;
            let inner_rx = (rx - half_width).max(0.0);
            let inner_ry = (ry - half_width).max(0.0);
            let steps = 64usize;
            let mut vertices = Vec::with_capacity(steps * 6);
            for index in 0..steps {
                let a = 2.0 * PI * index as f64 / steps as f64;
                let b = 2.0 * PI * (index + 1) as f64 / steps as f64;
                let outer_a = (cx + a.cos() * outer_rx, cy + a.sin() * outer_ry);
                let inner_a = (cx + a.cos() * inner_rx, cy + a.sin() * inner_ry);
                let inner_b = (cx + b.cos() * inner_rx, cy + b.sin() * inner_ry);
                let outer_b = (cx + b.cos() * outer_rx, cy + b.sin() * outer_ry);
                push_triangle(&mut vertices, outer_a, inner_a, inner_b, stroke);
                push_triangle(&mut vertices, outer_a, inner_b, outer_b, stroke);
            }
            self.draw_gpu_triangles(vertices);
        }
    }

    fn draw_gpu_triangles(&mut self, vertices: Vec<([f32; 2], gpu::GpuColor)>) {
        if let Some(gpu) = self.gpu.as_mut() {
            gpu.draw_triangles(vertices);
            self.render_dirty = true;
            self.offscreen_dirty = true;
            self.pixels_stale = true;
        }
    }
}

#[pyfunction]
fn health_check() -> &'static str {
    "rust-canvas"
}

#[pyfunction]
fn native_window_available() -> bool {
    runtime_native_window_available()
}

#[pyfunction]
fn gpu_available() -> bool {
    gpu::GpuRenderer::is_available()
}

#[pymodule]
fn _canvas(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(health_check, m)?)?;
    m.add_function(wrap_pyfunction!(native_window_available, m)?)?;
    m.add_function(wrap_pyfunction!(gpu_available, m)?)?;
    m.add_class::<Canvas>()?;
    Ok(())
}

fn runtime_event_to_pyobject(py: Python<'_>, event: RuntimeEvent) -> PyResult<Py<PyAny>> {
    let dict = PyDict::new_bound(py);
    dict.set_item("type", event.event_type)?;
    if let Some(x) = event.x {
        dict.set_item("x", x)?;
    }
    if let Some(y) = event.y {
        dict.set_item("y", y)?;
    }
    if let Some(dx) = event.dx {
        dict.set_item("dx", dx)?;
    }
    if let Some(dy) = event.dy {
        dict.set_item("dy", dy)?;
    }
    if let Some(button) = event.button {
        dict.set_item("button", button)?;
    }
    if let Some(scroll_x) = event.scroll_x {
        dict.set_item("scroll_x", scroll_x)?;
    }
    if let Some(scroll_y) = event.scroll_y {
        dict.set_item("scroll_y", scroll_y)?;
    }
    if let Some(modifiers) = event.modifiers {
        dict.set_item("modifiers", modifiers)?;
    }
    if let Some(key) = event.key {
        if !key.is_empty() {
            dict.set_item("key", key)?;
        }
    }
    if let Some(code) = event.code {
        if !code.is_empty() {
            dict.set_item("code", code)?;
        }
    }
    if let Some(text) = event.text {
        dict.set_item("text", text)?;
    }
    if let Some(width) = event.width {
        dict.set_item("width", width)?;
    }
    if let Some(height) = event.height {
        dict.set_item("height", height)?;
    }
    if let Some(pixel_density) = event.pixel_density {
        dict.set_item("pixel_density", pixel_density)?;
    }
    if let Some(coordinates) = event.coordinates {
        dict.set_item("coordinates", coordinates)?;
    }
    Ok(dict.into_any().unbind())
}

fn validate_mode_and_renderer(mode: &str, renderer: &str) -> PyResult<()> {
    if mode != SUPPORTED_MODE && mode != INTERACTIVE_MODE {
        return Err(PyValueError::new_err(format!(
            "Unsupported canvas mode {mode:?}; supported modes are {SUPPORTED_MODE:?} and {INTERACTIVE_MODE:?}."
        )));
    }
    validate_renderer(renderer)
}

fn validate_renderer(renderer: &str) -> PyResult<()> {
    if renderer != SUPPORTED_RENDERER {
        return Err(PyValueError::new_err(format!(
            "Unsupported renderer {renderer:?}; only {SUPPORTED_RENDERER:?} is implemented."
        )));
    }
    Ok(())
}

fn physical_dimensions(width: i64, height: i64, pixel_density: f64) -> PyResult<(usize, usize)> {
    if width <= 0 || height <= 0 {
        return Err(PyValueError::new_err(
            "Canvas width and height must be positive.",
        ));
    }
    if pixel_density <= 0.0 || !pixel_density.is_finite() {
        return Err(PyValueError::new_err("Pixel density must be positive."));
    }
    let physical_width = ((width as f64 * pixel_density).round() as i64).max(1) as usize;
    let physical_height = ((height as f64 * pixel_density).round() as i64).max(1) as usize;
    Ok((physical_width, physical_height))
}

fn parse_style(style: &Bound<'_, PyAny>) -> PyResult<Style> {
    let dict = style.downcast::<PyDict>()?;
    let fill = parse_optional_rgba(dict, "fill")?;
    let stroke = parse_optional_rgba(dict, "stroke")?;
    let stroke_weight = dict
        .get_item("stroke_weight")?
        .ok_or_else(|| PyValueError::new_err("Style payload missing 'stroke_weight'."))?
        .extract::<f64>()?;
    let blend_mode = dict
        .get_item("blend_mode")?
        .ok_or_else(|| PyValueError::new_err("Style payload missing 'blend_mode'."))?
        .extract::<String>()?;
    let erasing = dict
        .get_item("erasing")?
        .ok_or_else(|| PyValueError::new_err("Style payload missing 'erasing'."))?
        .extract::<bool>()?;
    let image_sampling = dict
        .get_item("image_sampling")?
        .map(|value| value.extract::<String>())
        .transpose()?
        .unwrap_or_else(|| "linear".to_string());
    Ok(Style {
        fill,
        stroke,
        stroke_weight,
        blend_mode,
        erasing,
        image_sampling,
    })
}

fn parse_optional_rgba(dict: &Bound<'_, PyDict>, key: &str) -> PyResult<Option<Rgba>> {
    let Some(value) = dict.get_item(key)? else {
        return Err(PyValueError::new_err(format!(
            "Style payload missing {key:?}."
        )));
    };
    if value.is_none() {
        Ok(None)
    } else {
        Ok(Some(Rgba::from_tuple(value.extract::<(u8, u8, u8, u8)>()?)))
    }
}

fn ensure_supported_style(style: &Style) -> PyResult<()> {
    if style.stroke_weight < 0.0 || !style.stroke_weight.is_finite() {
        return Err(PyValueError::new_err("stroke_weight cannot be negative."));
    }
    ensure_supported_blend_mode(&style.blend_mode)
}

fn ensure_supported_blend_mode(mode: &str) -> PyResult<()> {
    if is_supported_blend_mode(mode) {
        Ok(())
    } else {
        Err(PyValueError::new_err(format!(
            "Unsupported blend mode {mode:?} for p5_canvas."
        )))
    }
}

fn is_supported_blend_mode(mode: &str) -> bool {
    matches!(
        mode,
        BLEND_MODE_BLEND
            | BLEND_MODE_REPLACE
            | BLEND_MODE_ADD
            | BLEND_MODE_DARKEST
            | BLEND_MODE_LIGHTEST
            | BLEND_MODE_DIFFERENCE
            | BLEND_MODE_EXCLUSION
            | BLEND_MODE_MULTIPLY
            | BLEND_MODE_SCREEN
    )
}

fn stroke_width(stroke_weight: f64, pixel_density: f64) -> f64 {
    (stroke_weight * pixel_density).round().max(1.0)
}

fn validate_rgba_buffer(length: usize, width: usize, height: usize) -> PyResult<()> {
    let expected = width
        .checked_mul(height)
        .and_then(|pixels| pixels.checked_mul(4))
        .ok_or_else(|| PyValueError::new_err("Image dimensions are too large."))?;
    if length == expected {
        Ok(())
    } else {
        Err(PyValueError::new_err(format!(
            "RGBA buffer length must be {expected}, got {length}."
        )))
    }
}

fn scale_rect(rect: (i64, i64, i64, i64), pixel_density: f64) -> (i64, i64, i64, i64) {
    (
        (rect.0 as f64 * pixel_density).round() as i64,
        (rect.1 as f64 * pixel_density).round() as i64,
        (rect.2 as f64 * pixel_density).round() as i64,
        (rect.3 as f64 * pixel_density).round() as i64,
    )
}

fn image_to_canvas_matrix(
    matrix: Matrix,
    dx: f64,
    dy: f64,
    dw: f64,
    dh: f64,
    sw: usize,
    sh: usize,
    pixel_density: f64,
) -> Matrix {
    let physical = (
        matrix.0 * pixel_density,
        matrix.1 * pixel_density,
        matrix.2 * pixel_density,
        matrix.3 * pixel_density,
        matrix.4 * pixel_density,
        matrix.5 * pixel_density,
    );
    matrix_multiply(
        matrix_multiply(physical, (1.0, 0.0, 0.0, 1.0, dx, dy)),
        (dw / sw as f64, 0.0, 0.0, dh / sh as f64, 0.0, 0.0),
    )
}

fn matrix_multiply(left: Matrix, right: Matrix) -> Matrix {
    (
        left.0 * right.0 + left.2 * right.1,
        left.1 * right.0 + left.3 * right.1,
        left.0 * right.2 + left.2 * right.3,
        left.1 * right.2 + left.3 * right.3,
        left.0 * right.4 + left.2 * right.5 + left.4,
        left.1 * right.4 + left.3 * right.5 + left.5,
    )
}

fn matrix_transform_point(matrix: Matrix, x: f64, y: f64) -> Point {
    (
        matrix.0 * x + matrix.2 * y + matrix.4,
        matrix.1 * x + matrix.3 * y + matrix.5,
    )
}

fn matrix_determinant(matrix: Matrix) -> f64 {
    matrix.0 * matrix.3 - matrix.1 * matrix.2
}

fn matrix_inverse(matrix: Matrix) -> Option<Matrix> {
    let determinant = matrix_determinant(matrix);
    if determinant.abs() <= f64::EPSILON {
        return None;
    }
    let inv_det = 1.0 / determinant;
    let a = matrix.3 * inv_det;
    let b = -matrix.1 * inv_det;
    let c = -matrix.2 * inv_det;
    let d = matrix.0 * inv_det;
    let e = -(a * matrix.4 + c * matrix.5);
    let f = -(b * matrix.4 + d * matrix.5);
    Some((a, b, c, d, e, f))
}

fn affine_bounds(
    matrix: Matrix,
    width: usize,
    height: usize,
    canvas_width: usize,
    canvas_height: usize,
) -> Option<(usize, usize, usize, usize)> {
    let corners = [
        matrix_transform_point(matrix, 0.0, 0.0),
        matrix_transform_point(matrix, width as f64, 0.0),
        matrix_transform_point(matrix, width as f64, height as f64),
        matrix_transform_point(matrix, 0.0, height as f64),
    ];
    let min_x = corners
        .iter()
        .map(|point| point.0)
        .fold(f64::INFINITY, f64::min)
        .floor()
        .max(0.0) as usize;
    let min_y = corners
        .iter()
        .map(|point| point.1)
        .fold(f64::INFINITY, f64::min)
        .floor()
        .max(0.0) as usize;
    let max_x = corners
        .iter()
        .map(|point| point.0)
        .fold(f64::NEG_INFINITY, f64::max)
        .ceil()
        .min(canvas_width as f64)
        .max(0.0) as usize;
    let max_y = corners
        .iter()
        .map(|point| point.1)
        .fold(f64::NEG_INFINITY, f64::max)
        .ceil()
        .min(canvas_height as f64)
        .max(0.0) as usize;
    if max_x <= min_x || max_y <= min_y {
        None
    } else {
        Some((min_x, min_y, max_x - min_x, max_y - min_y))
    }
}

fn axis_aligned_image_destination(
    matrix: Matrix,
    width: usize,
    height: usize,
    canvas_width: usize,
    canvas_height: usize,
) -> Option<(usize, usize, usize, usize)> {
    if matrix.1.abs() > f64::EPSILON || matrix.2.abs() > f64::EPSILON {
        return None;
    }
    if matrix.0 <= 0.0 || matrix.3 <= 0.0 {
        return None;
    }
    let left = matrix.4.round();
    let top = matrix.5.round();
    let dest_width = (matrix.0 * width as f64).round();
    let dest_height = (matrix.3 * height as f64).round();
    if left < 0.0 || top < 0.0 || dest_width <= 0.0 || dest_height <= 0.0 {
        return None;
    }
    let right = left + dest_width;
    let bottom = top + dest_height;
    if right > canvas_width as f64 || bottom > canvas_height as f64 {
        return None;
    }
    Some((
        left as usize,
        top as usize,
        dest_width as usize,
        dest_height as usize,
    ))
}

fn clipped_source_rect(
    rect: (i64, i64, i64, i64),
    width: usize,
    height: usize,
) -> Option<(usize, usize, usize, usize)> {
    let (x, y, w, h) = rect;
    if w <= 0 || h <= 0 {
        return None;
    }
    let left = x.clamp(0, width as i64) as usize;
    let top = y.clamp(0, height as i64) as usize;
    let right = (x + w).clamp(0, width as i64) as usize;
    let bottom = (y + h).clamp(0, height as i64) as usize;
    if right <= left || bottom <= top {
        None
    } else {
        Some((left, top, right - left, bottom - top))
    }
}

fn clipped_dest_rect(
    rect: (i64, i64, i64, i64),
    width: usize,
    height: usize,
) -> Option<(usize, usize, usize, usize)> {
    clipped_source_rect(rect, width, height)
}

#[allow(clippy::too_many_arguments)]
fn blit_scaled_region(
    dst: &mut [u8],
    present_pixels: &mut [u32],
    dst_width: usize,
    src: &[u8],
    src_width: usize,
    sx: usize,
    sy: usize,
    sw: usize,
    sh: usize,
    dx: usize,
    dy: usize,
    dw: usize,
    dh: usize,
    erasing: bool,
    blend_mode: &str,
    sampling: &str,
) {
    if sw == 0 || sh == 0 || dw == 0 || dh == 0 {
        return;
    }
    let nearest = sampling == "nearest";
    let default_blend = blend_mode == BLEND_MODE_BLEND;
    for out_y in 0..dh {
        let src_y = if nearest {
            sy + (out_y * sh / dh).min(sh - 1)
        } else {
            sy + (((out_y as f64 + 0.5) * sh as f64 / dh as f64).floor() as usize).min(sh - 1)
        };
        for out_x in 0..dw {
            let src_x = if nearest {
                sx + (out_x * sw / dw).min(sw - 1)
            } else {
                sx + (((out_x as f64 + 0.5) * sw as f64 / dw as f64).floor() as usize).min(sw - 1)
            };
            let src_offset = (src_y * src_width + src_x) * 4;
            let src_pixel = &src[src_offset..src_offset + 4];
            if src_pixel[3] == 0 {
                continue;
            }
            let dst_pixel_index = (dy + out_y) * dst_width + dx + out_x;
            let dst_offset = dst_pixel_index * 4;
            let dst_pixel = &mut dst[dst_offset..dst_offset + 4];
            if erasing {
                dst_pixel[3] = dst_pixel[3].saturating_sub(src_pixel[3]);
            } else if default_blend && src_pixel[3] == 255 {
                dst_pixel.copy_from_slice(src_pixel);
            } else {
                blend_pixel(dst_pixel, src_pixel, blend_mode);
            }
            present_pixels[dst_pixel_index] = rgba_to_present_pixel(dst_pixel);
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn blit_affine_region(
    dst: &mut [u8],
    present_pixels: &mut [u32],
    dst_width: usize,
    src: &[u8],
    src_width: usize,
    sx: usize,
    sy: usize,
    sw: usize,
    sh: usize,
    dx: usize,
    dy: usize,
    dw: usize,
    dh: usize,
    canvas_to_image: Matrix,
    erasing: bool,
    blend_mode: &str,
    sampling: &str,
) {
    if sw == 0 || sh == 0 || dw == 0 || dh == 0 {
        return;
    }
    let _sampling = sampling;
    let default_blend = blend_mode == BLEND_MODE_BLEND;
    let (a, b, c, d, e, f) = canvas_to_image;
    for out_y in 0..dh {
        let canvas_y = dy + out_y;
        let sample_y = canvas_y as f64 + 0.5;
        let mut local_x = a * (dx as f64 + 0.5) + c * sample_y + e;
        let mut local_y = b * (dx as f64 + 0.5) + d * sample_y + f;
        for out_x in 0..dw {
            let canvas_x = dx + out_x;
            if local_x < 0.0 || local_y < 0.0 || local_x >= sw as f64 || local_y >= sh as f64 {
                local_x += a;
                local_y += b;
                continue;
            }
            let sample_x = local_x.floor().clamp(0.0, (sw - 1) as f64) as usize;
            let sample_y = local_y.floor().clamp(0.0, (sh - 1) as f64) as usize;
            let src_offset = ((sy + sample_y) * src_width + sx + sample_x) * 4;
            let src_pixel = &src[src_offset..src_offset + 4];
            if src_pixel[3] == 0 {
                local_x += a;
                local_y += b;
                continue;
            }
            let dst_pixel_index = canvas_y * dst_width + canvas_x;
            let dst_offset = dst_pixel_index * 4;
            let dst_pixel = &mut dst[dst_offset..dst_offset + 4];
            if erasing {
                dst_pixel[3] = dst_pixel[3].saturating_sub(src_pixel[3]);
            } else if default_blend && src_pixel[3] == 255 {
                dst_pixel.copy_from_slice(src_pixel);
            } else {
                blend_pixel(dst_pixel, src_pixel, blend_mode);
            }
            present_pixels[dst_pixel_index] = rgba_to_present_pixel(dst_pixel);
            local_x += a;
            local_y += b;
        }
    }
}

fn draw_polygon_overlay(
    overlay: &mut OverlayRegion<'_>,
    points: &[Point],
    style: &Style,
    close: bool,
    pixel_density: f64,
) {
    if points.len() == 1 {
        let color = style.stroke.or(style.fill);
        if let Some(color) = color {
            fill_disc(
                overlay,
                points[0].0,
                points[0].1,
                (style.stroke_weight * pixel_density / 2.0).max(0.5),
                color,
            );
        }
        return;
    }

    if close && points.len() >= 3 {
        if let Some(fill) = style.fill {
            fill_polygon(overlay, points, fill);
        }
    }

    if let Some(stroke) = style.stroke {
        draw_polyline_stroke(
            overlay,
            points,
            close,
            stroke_width(style.stroke_weight, pixel_density),
            stroke,
        );
    }
}

fn draw_axis_aligned_ellipse(
    overlay: &mut OverlayRegion<'_>,
    cx: f64,
    cy: f64,
    rx: f64,
    ry: f64,
    style: &Style,
    pixel_density: f64,
) {
    if rx <= 0.0 || ry <= 0.0 {
        return;
    }
    if let Some(fill) = style.fill {
        fill_axis_aligned_ellipse(overlay, cx, cy, rx, ry, fill);
    }
    if let Some(stroke) = style.stroke {
        stroke_axis_aligned_ellipse(
            overlay,
            cx,
            cy,
            rx,
            ry,
            stroke_width(style.stroke_weight, pixel_density),
            stroke,
        );
    }
}

fn fill_axis_aligned_ellipse(
    overlay: &mut OverlayRegion<'_>,
    cx: f64,
    cy: f64,
    rx: f64,
    ry: f64,
    color: Rgba,
) {
    let inv_rx2 = 1.0 / (rx * rx);
    let inv_ry2 = 1.0 / (ry * ry);
    for y in overlay.min_y..overlay.max_y() {
        let dy = y as f64 + 0.5 - cy;
        let dy2 = dy * dy * inv_ry2;
        if dy2 > 1.0 {
            continue;
        }
        for x in overlay.min_x..overlay.max_x() {
            let dx = x as f64 + 0.5 - cx;
            if dx * dx * inv_rx2 + dy2 <= 1.0 {
                overlay.set_pixel(x, y, color);
            }
        }
    }
}

fn stroke_axis_aligned_ellipse(
    overlay: &mut OverlayRegion<'_>,
    cx: f64,
    cy: f64,
    rx: f64,
    ry: f64,
    stroke_width: f64,
    color: Rgba,
) {
    let half_width = (stroke_width / 2.0).max(0.5);
    let outer_rx = rx + half_width;
    let outer_ry = ry + half_width;
    let inner_rx = (rx - half_width).max(0.0);
    let inner_ry = (ry - half_width).max(0.0);
    let outer_inv_rx2 = 1.0 / (outer_rx * outer_rx);
    let outer_inv_ry2 = 1.0 / (outer_ry * outer_ry);
    let has_inner = inner_rx > 0.0 && inner_ry > 0.0;
    let inner_inv_rx2 = if has_inner {
        1.0 / (inner_rx * inner_rx)
    } else {
        0.0
    };
    let inner_inv_ry2 = if has_inner {
        1.0 / (inner_ry * inner_ry)
    } else {
        0.0
    };

    for y in overlay.min_y..overlay.max_y() {
        let dy = y as f64 + 0.5 - cy;
        let outer_dy2 = dy * dy * outer_inv_ry2;
        if outer_dy2 > 1.0 {
            continue;
        }
        let inner_dy2 = dy * dy * inner_inv_ry2;
        for x in overlay.min_x..overlay.max_x() {
            let dx = x as f64 + 0.5 - cx;
            let outer = dx * dx * outer_inv_rx2 + outer_dy2;
            if outer > 1.0 {
                continue;
            }
            let inside_inner = has_inner && dx * dx * inner_inv_rx2 + inner_dy2 <= 1.0;
            if !inside_inner {
                overlay.set_pixel(x, y, color);
            }
        }
    }
}

fn fill_polygon(overlay: &mut OverlayRegion<'_>, points: &[Point], color: Rgba) {
    for y in overlay.min_y..overlay.max_y() {
        for x in overlay.min_x..overlay.max_x() {
            let sample = (x as f64 + 0.5, y as f64 + 0.5);
            if point_in_polygon(sample, points) {
                overlay.set_pixel(x, y, color);
            }
        }
    }
}

fn draw_polyline_stroke(
    overlay: &mut OverlayRegion<'_>,
    points: &[Point],
    close: bool,
    stroke_width: f64,
    color: Rgba,
) {
    if points.len() < 2 {
        return;
    }
    for pair in points.windows(2) {
        stroke_segment(overlay, pair[0], pair[1], stroke_width, color);
    }
    if close {
        stroke_segment(
            overlay,
            *points.last().expect("non-empty points"),
            points[0],
            stroke_width,
            color,
        );
    }
}

fn stroke_segment(
    overlay: &mut OverlayRegion<'_>,
    p1: Point,
    p2: Point,
    stroke_width: f64,
    color: Rgba,
) {
    let radius = (stroke_width / 2.0).max(0.5);
    let radius_squared = radius * radius;
    for y in overlay.min_y..overlay.max_y() {
        for x in overlay.min_x..overlay.max_x() {
            let sample = (x as f64 + 0.5, y as f64 + 0.5);
            if distance_to_segment_squared(sample, p1, p2) <= radius_squared {
                overlay.set_pixel(x, y, color);
            }
        }
    }
}

fn fill_disc(overlay: &mut OverlayRegion<'_>, cx: f64, cy: f64, radius: f64, color: Rgba) {
    let radius_squared = radius * radius;
    for y in overlay.min_y..overlay.max_y() {
        for x in overlay.min_x..overlay.max_x() {
            let dx = x as f64 + 0.5 - cx;
            let dy = y as f64 + 0.5 - cy;
            if dx * dx + dy * dy <= radius_squared {
                overlay.set_pixel(x, y, color);
            }
        }
    }
}

fn ellipse_bounds(
    cx: f64,
    cy: f64,
    rx: f64,
    ry: f64,
    padding: f64,
    width: usize,
    height: usize,
) -> (usize, usize, usize, usize) {
    (
        (cx - rx - padding).floor().max(0.0) as usize,
        (cy - ry - padding).floor().max(0.0) as usize,
        (cx + rx + padding).ceil().min(width as f64).max(0.0) as usize,
        (cy + ry + padding).ceil().min(height as f64).max(0.0) as usize,
    )
}

fn clipped_bounds(
    points: &[Point],
    padding: f64,
    width: usize,
    height: usize,
) -> (usize, usize, usize, usize) {
    let min_x = points
        .iter()
        .map(|point| point.0)
        .fold(f64::INFINITY, f64::min)
        - padding;
    let min_y = points
        .iter()
        .map(|point| point.1)
        .fold(f64::INFINITY, f64::min)
        - padding;
    let max_x = points
        .iter()
        .map(|point| point.0)
        .fold(f64::NEG_INFINITY, f64::max)
        + padding;
    let max_y = points
        .iter()
        .map(|point| point.1)
        .fold(f64::NEG_INFINITY, f64::max)
        + padding;
    (
        min_x.floor().max(0.0) as usize,
        min_y.floor().max(0.0) as usize,
        max_x.ceil().min(width as f64).max(0.0) as usize,
        max_y.ceil().min(height as f64).max(0.0) as usize,
    )
}

fn point_in_polygon(sample: Point, points: &[Point]) -> bool {
    let (x, y) = sample;
    let mut inside = false;
    let mut previous = *points.last().expect("polygon has at least one point");
    for &current in points {
        let intersects = ((current.1 > y) != (previous.1 > y))
            && (x
                < (previous.0 - current.0) * (y - current.1) / (previous.1 - current.1)
                    + current.0);
        if intersects {
            inside = !inside;
        }
        previous = current;
    }
    inside
}

fn distance_to_segment_squared(point: Point, p1: Point, p2: Point) -> f64 {
    let vx = p2.0 - p1.0;
    let vy = p2.1 - p1.1;
    let wx = point.0 - p1.0;
    let wy = point.1 - p1.1;
    let length_squared = vx * vx + vy * vy;
    if length_squared <= f64::EPSILON {
        let dx = point.0 - p1.0;
        let dy = point.1 - p1.1;
        return dx * dx + dy * dy;
    }
    let t = ((wx * vx + wy * vy) / length_squared).clamp(0.0, 1.0);
    let projection = (p1.0 + t * vx, p1.1 + t * vy);
    let dx = point.0 - projection.0;
    let dy = point.1 - projection.1;
    dx * dx + dy * dy
}

fn alpha_composite_pixel(dst: &mut [u8], src: &[u8]) {
    let src_alpha = src[3] as u32;
    if src_alpha == 255 {
        dst.copy_from_slice(src);
        return;
    }
    let dst_alpha = dst[3] as u32;
    if src_alpha == 0 {
        return;
    }
    let inv_src_alpha = 255 - src_alpha;
    let out_alpha = src_alpha + (dst_alpha * inv_src_alpha + 127) / 255;
    if out_alpha == 0 {
        dst.copy_from_slice(&[0, 0, 0, 0]);
        return;
    }
    for channel in 0..3 {
        let src_premul = src[channel] as u32 * src_alpha;
        let dst_premul = dst[channel] as u32 * dst_alpha * inv_src_alpha / 255;
        dst[channel] = ((src_premul + dst_premul + out_alpha / 2) / out_alpha) as u8;
    }
    dst[3] = out_alpha as u8;
}

fn blend_pixel(dst: &mut [u8], src: &[u8], mode: &str) {
    if mode == BLEND_MODE_BLEND {
        alpha_composite_pixel(dst, src);
        return;
    }
    if mode == BLEND_MODE_REPLACE {
        alpha_composite_pixel(dst, src);
        return;
    }
    let alpha = src[3] as u32;
    if alpha == 0 {
        return;
    }
    let base = [dst[0], dst[1], dst[2]];
    let blend = [
        blend_channel(base[0], src[0], mode),
        blend_channel(base[1], src[1], mode),
        blend_channel(base[2], src[2], mode),
    ];
    let inv_alpha = 255 - alpha;
    for channel in 0..3 {
        dst[channel] =
            ((blend[channel] as u32 * alpha + base[channel] as u32 * inv_alpha + 127) / 255) as u8;
    }
}

fn blend_channel(base: u8, src: u8, mode: &str) -> u8 {
    match mode {
        BLEND_MODE_ADD => base.saturating_add(src),
        BLEND_MODE_DARKEST => base.min(src),
        BLEND_MODE_LIGHTEST => base.max(src),
        BLEND_MODE_DIFFERENCE => base.abs_diff(src),
        BLEND_MODE_EXCLUSION => {
            let base = base as u32;
            let src = src as u32;
            (base + src - (2 * base * src + 127) / 255).min(255) as u8
        }
        BLEND_MODE_MULTIPLY => ((base as u32 * src as u32 + 127) / 255) as u8,
        BLEND_MODE_SCREEN => {
            let inv = (255 - base as u32) * (255 - src as u32);
            (255 - (inv + 127) / 255) as u8
        }
        _ => src,
    }
}

fn fill_rgba_buffer(pixels: &mut [u8], color: &[u8; 4]) {
    if pixels.is_empty() {
        return;
    }
    let first_len = pixels.len().min(4);
    pixels[..first_len].copy_from_slice(&color[..first_len]);
    let mut filled = first_len;
    while filled < pixels.len() {
        let copy_len = filled.min(pixels.len() - filled);
        pixels.copy_within(0..copy_len, filled);
        filled += copy_len;
    }
}

fn rgba_to_present_pixel(rgba: &[u8]) -> u32 {
    ((rgba[3] as u32) << 24) | ((rgba[0] as u32) << 16) | ((rgba[1] as u32) << 8) | rgba[2] as u32
}

fn gpu_color(color: Rgba) -> gpu::GpuColor {
    gpu::GpuColor {
        r: color.r,
        g: color.g,
        b: color.b,
        a: color.a,
    }
}

fn push_triangle(
    vertices: &mut Vec<([f32; 2], gpu::GpuColor)>,
    a: Point,
    b: Point,
    c: Point,
    color: Rgba,
) {
    let color = gpu_color(color);
    vertices.push((point_to_gpu(a), color));
    vertices.push((point_to_gpu(b), color));
    vertices.push((point_to_gpu(c), color));
}

fn point_to_gpu(point: Point) -> [f32; 2] {
    [point.0 as f32, point.1 as f32]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn health_check_reports_canvas_backend() {
        assert_eq!(health_check(), "rust-canvas");
        assert_eq!(native_window_available(), runtime_native_window_available());
    }

    #[test]
    fn canvas_tracks_logical_and_physical_dimensions() {
        let canvas = Canvas::new(10, 8, 2.0, SUPPORTED_MODE, SUPPORTED_RENDERER).unwrap();

        assert_eq!(canvas.dimensions(), (10, 8, 20, 16, 2.0));
        assert_eq!(canvas.pixels.len(), 20 * 16 * 4);
    }

    #[test]
    fn canvas_rejects_invalid_dimensions_and_density() {
        assert!(Canvas::new(0, 8, 1.0, SUPPORTED_MODE, SUPPORTED_RENDERER).is_err());
        assert!(Canvas::new(10, 8, 0.0, SUPPORTED_MODE, SUPPORTED_RENDERER).is_err());
    }

    #[test]
    fn background_clear_and_pixel_update_round_trip() {
        let mut canvas = Canvas::new(2, 1, 1.0, SUPPORTED_MODE, SUPPORTED_RENDERER).unwrap();
        canvas.background((10, 20, 30, 255));
        assert_eq!(canvas.load_pixels(), vec![10, 20, 30, 255, 10, 20, 30, 255]);

        canvas
            .update_pixels(vec![255, 0, 0, 255, 0, 0, 255, 255])
            .unwrap();
        assert_eq!(canvas.load_pixels(), vec![255, 0, 0, 255, 0, 0, 255, 255]);

        canvas.clear();
        assert_eq!(canvas.load_pixels(), vec![0; 8]);
    }

    #[test]
    fn gpu_status_reports_available_or_clear_error() {
        let canvas = Canvas::new(4, 4, 1.0, SUPPORTED_MODE, SUPPORTED_RENDERER).unwrap();

        if canvas.gpu_available() {
            assert_eq!(canvas.gpu_status(), "available");
        } else {
            assert_ne!(canvas.gpu_status(), "available");
        }
    }

    #[test]
    fn gpu_path_renders_background_and_triangle_when_available() {
        let mut canvas = Canvas::new(8, 8, 1.0, SUPPORTED_MODE, SUPPORTED_RENDERER).unwrap();
        if !canvas.gpu_available() {
            return;
        }

        canvas.begin_frame();
        canvas.background((255, 255, 255, 255));
        canvas.draw_gpu_polygon(
            &[(1.0, 1.0), (6.0, 1.0), (1.0, 6.0)],
            &Style {
                fill: Some(Rgba {
                    r: 255,
                    g: 0,
                    b: 0,
                    a: 255,
                }),
                stroke: None,
                stroke_weight: 1.0,
                blend_mode: BLEND_MODE_BLEND.to_string(),
                erasing: false,
                image_sampling: "linear".to_string(),
            },
            true,
            1.0,
        );
        canvas.end_frame();

        let pixels = canvas.load_pixels();
        assert!(pixels.chunks_exact(4).any(|rgba| rgba == [255, 0, 0, 255]));
        assert!(pixels
            .chunks_exact(4)
            .any(|rgba| rgba == [255, 255, 255, 255]));
    }

    #[test]
    fn gpu_overlay_after_cpu_upload_does_not_replay_previous_clear() {
        let mut canvas = Canvas::new(8, 8, 1.0, SUPPORTED_MODE, SUPPORTED_RENDERER).unwrap();
        if !canvas.gpu_available() {
            return;
        }

        canvas.begin_frame();
        canvas.background((255, 255, 255, 255));
        canvas.render_gpu_frame(true);

        let preserved_pixel_offset = (7 * canvas.physical_width + 7) * 4;
        canvas.pixels[preserved_pixel_offset..preserved_pixel_offset + 4]
            .copy_from_slice(&[255, 0, 0, 255]);
        canvas.upload_cpu_pixels().unwrap();
        canvas.draw_gpu_polygon(
            &[(1.0, 1.0), (3.0, 1.0), (1.0, 3.0)],
            &Style {
                fill: Some(Rgba {
                    r: 0,
                    g: 0,
                    b: 255,
                    a: 255,
                }),
                stroke: None,
                stroke_weight: 1.0,
                blend_mode: BLEND_MODE_BLEND.to_string(),
                erasing: false,
                image_sampling: "linear".to_string(),
            },
            true,
            1.0,
        );
        canvas.end_frame();

        let pixels = canvas.load_pixels();
        assert_eq!(
            &pixels[preserved_pixel_offset..preserved_pixel_offset + 4],
            &[255, 0, 0, 255]
        );
        assert!(pixels.chunks_exact(4).any(|rgba| rgba == [0, 0, 255, 255]));
    }

    #[test]
    fn interactive_runtime_primitives_track_open_and_close_state() {
        let mut canvas = Canvas::new(10, 8, 2.0, INTERACTIVE_MODE, SUPPORTED_RENDERER).unwrap();

        assert_eq!(canvas.display_density(), 2.0);
        assert!(!canvas.should_close());
        assert!(canvas.poll_events().unwrap().is_empty());
        assert_eq!(
            canvas.native_window_available(),
            runtime_native_window_available()
        );

        canvas.close();
        assert!(canvas.should_close());
    }
}
