"""Native Pyglet WEBGL-style renderer backed by a depth-tested OpenGL path."""

from __future__ import annotations

import ctypes
import math
from collections.abc import Sequence
from typing import Any, cast

from p5.assets.image import Image
from p5.backends.pyglet_renderer import PygletRenderer
from p5.core.color import Color
from p5.drawing.renderer3d import (
    Camera3D,
    Light3D,
    Material3D,
    Mesh3D,
    Model3D,
    PerspectiveProjection,
    Projection3D,
    Shader3D,
    ShaderUniformValue,
    Texture3D,
    Vec3,
)
from p5.exceptions import ShaderCompilationError, ShaderUniformError


def _normalize(v: Vec3) -> Vec3:
    length = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
    if length <= 0:
        return Vec3(0.0, 0.0, 1.0)
    return Vec3(v.x / length, v.y / length, v.z / length)


def _subtract(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(a.x - b.x, a.y - b.y, a.z - b.z)


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return Vec3(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    )


def _dot(a: Vec3, b: Vec3) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def _multiply_matrix(
    a: tuple[tuple[float, ...], ...], b: tuple[tuple[float, ...], ...]
) -> tuple[tuple[float, ...], ...]:
    return tuple(
        tuple(sum(a[row][k] * b[k][col] for k in range(4)) for col in range(4)) for row in range(4)
    )


def _flatten_column_major(matrix: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    return tuple(matrix[row][col] for col in range(4) for row in range(4))


def _triangulate(face: tuple[int, ...]) -> list[tuple[int, int, int]]:
    if len(face) < 3:
        return []
    return [(face[0], face[index], face[index + 1]) for index in range(1, len(face) - 1)]


class PygletWebGLRenderer(PygletRenderer):
    """Pyglet renderer with a native OpenGL draw path for WEBGL sketches."""

    three_d = True

    @staticmethod
    def native_gl_supported(pyglet: Any) -> bool:
        gl = getattr(pyglet, "gl", None)
        if gl is None:
            return False
        required = (
            "glViewport",
            "glEnable",
            "glDepthMask",
            "glClearColor",
            "glClear",
            "glUseProgram",
            "glCreateProgram",
            "glCreateShader",
            "glShaderSource",
            "glCompileShader",
            "glAttachShader",
            "glLinkProgram",
            "glGetShaderiv",
            "glGetProgramiv",
            "glGetUniformLocation",
            "glUniformMatrix4fv",
            "glUniform1f",
            "glUniform1i",
            "glUniform2f",
            "glUniform3f",
            "glUniform4f",
            "glUniformMatrix2fv",
            "glUniformMatrix3fv",
            "glActiveTexture",
            "glBindTexture",
            "glGenTextures",
            "glTexParameteri",
            "glTexImage2D",
            "glGenBuffers",
            "glBindBuffer",
            "glBufferData",
            "glGenVertexArrays",
            "glBindVertexArray",
            "glEnableVertexAttribArray",
            "glVertexAttribPointer",
            "glGetAttribLocation",
            "glDrawArrays",
        )
        return all(hasattr(gl, name) for name in required)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._camera = Camera3D()
        self._projection: Projection3D = PerspectiveProjection()
        self._lights: tuple[Light3D, ...] = ()
        self._material: Material3D | None = None
        self._texture: Texture3D | None = None
        self._active_shader: Shader3D | None = None
        self._shader_programs: dict[int, int] = {}
        self._default_shader: Shader3D | None = None
        self._fallback_texture_id: int | None = None
        self._queued_models: list[
            tuple[Model3D, Material3D | None, Texture3D | None, Shader3D | None]
        ] = []
        self._clear_color = (0.0, 0.0, 0.0, 0.0)

    def begin_frame(self) -> None:
        super().begin_frame()
        self._queued_models = []

    def background(self, color: Color) -> None:
        self._clear_color = (
            color.r / 255.0,
            color.g / 255.0,
            color.b / 255.0,
            color.a / 255.0,
        )
        super().background(color)

    def set_camera(self, camera: Camera3D) -> None:
        self._camera = camera

    def set_projection(self, projection: Projection3D) -> None:
        self._projection = projection

    def set_lights(self, lights: Sequence[Light3D]) -> None:
        self._lights = tuple(lights)

    def set_material(self, material: Material3D | None) -> None:
        self._material = material

    def set_texture(self, texture: Texture3D | None) -> None:
        self._texture = texture

    def use_shader(self, shader: Shader3D | None) -> None:
        self._active_shader = shader

    def set_shader_uniform(self, name: str, value: ShaderUniformValue) -> None:
        if self._active_shader is None:
            raise ShaderUniformError(
                f"Cannot set uniform {name!r} without an active shader on backend 'pyglet'."
            )
        self._active_shader.set_uniform(name, value)

    def draw_model(
        self, model: Model3D, transform: tuple[tuple[float, ...], ...] | None = None
    ) -> None:
        del transform
        self._queued_models.append((model, self._material, self._texture, self._active_shader))

    def draw_mesh(
        self, mesh: Mesh3D, transform: tuple[tuple[float, ...], ...] | None = None
    ) -> None:
        del transform
        self.draw_model(Model3D(meshes=(mesh,)))

    def plane(self, width: float, height: float) -> None:
        del width, height

    def box(self, width: float, height: float, depth: float) -> None:
        del width, height, depth

    def sphere(self, radius: float, detail_x: int = 24, detail_y: int = 16) -> None:
        del radius, detail_x, detail_y

    def draw(self) -> None:
        if not self._queued_models:
            super().draw()
            return
        self._render_native_scene()

    def _render_native_scene(self) -> None:
        pyglet = self._load_pyglet()
        gl = pyglet.gl
        viewport = (0, 0, self.physical_width, self.physical_height)
        gl.glViewport(*viewport)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDepthMask(gl.GL_TRUE)
        gl.glClearColor(*self._clear_color)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        if self._batch is not None and not self._parity_active:
            self._batch.draw()

        projection = _projection_matrix(self._projection, self.width, self.height)
        view = _view_matrix(self._camera)
        mvp = _multiply_matrix(projection, view)

        for model, material, texture, shader in self._queued_models:
            active_shader = shader or self._default_shader_program_definition()
            program = self._program_for_shader(active_shader)
            gl.glUseProgram(program)
            self._apply_builtin_uniforms(gl, program, projection, view, mvp)
            self._apply_material_uniforms(gl, program, material)
            for uniform_name, uniform_value in active_shader.uniforms.items():
                self._apply_uniform(gl, program, uniform_name, uniform_value)
            texture_bound = self._bind_material_texture(gl, program, material, texture)
            self._draw_model_buffered(gl, program, model)
            if texture_bound:
                gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            gl.glUseProgram(0)
        gl.glDisable(gl.GL_DEPTH_TEST)

    def _default_shader_program_definition(self) -> Shader3D:
        if self._default_shader is None:
            self._default_shader = Shader3D(
                vertex_source="""
#version 150
in vec3 a_position;
in vec2 a_texcoord;
uniform mat4 u_model_view_projection;
out vec2 v_texcoord;
void main() {
    v_texcoord = a_texcoord;
    gl_Position = u_model_view_projection * vec4(a_position, 1.0);
}
""".strip(),
                fragment_source="""
#version 150
uniform vec4 u_color;
uniform sampler2D u_texture;
uniform bool u_use_texture;
in vec2 v_texcoord;
out vec4 fragColor;
void main() {
    fragColor = u_use_texture ? texture(u_texture, v_texcoord) : u_color;
}
""".strip(),
            )
        return self._default_shader

    def _draw_model_buffered(self, gl: Any, program: int, model: Model3D) -> None:
        vertex_data = self._vertex_data_for_model(model)
        if not vertex_data:
            return
        vertex_count = len(vertex_data) // 5
        data = (ctypes.c_float * len(vertex_data))(*vertex_data)
        vao = ctypes.c_uint()
        vbo = ctypes.c_uint()
        gl.glGenVertexArrays(1, ctypes.byref(vao))
        gl.glGenBuffers(1, ctypes.byref(vbo))
        gl.glBindVertexArray(vao.value)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo.value)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, ctypes.sizeof(data), data, gl.GL_STATIC_DRAW)

        stride = 5 * ctypes.sizeof(ctypes.c_float)
        position_location = gl.glGetAttribLocation(program, b"a_position")
        if position_location >= 0:
            gl.glEnableVertexAttribArray(position_location)
            gl.glVertexAttribPointer(
                position_location,
                3,
                gl.GL_FLOAT,
                gl.GL_FALSE,
                stride,
                ctypes.c_void_p(0),
            )
        texcoord_location = gl.glGetAttribLocation(program, b"a_texcoord")
        if texcoord_location >= 0:
            gl.glEnableVertexAttribArray(texcoord_location)
            gl.glVertexAttribPointer(
                texcoord_location,
                2,
                gl.GL_FLOAT,
                gl.GL_FALSE,
                stride,
                ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)),
            )

        gl.glDrawArrays(gl.GL_TRIANGLES, 0, vertex_count)

        if position_location >= 0:
            gl.glDisableVertexAttribArray(position_location)
        if texcoord_location >= 0:
            gl.glDisableVertexAttribArray(texcoord_location)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        gl.glBindVertexArray(0)
        gl.glDeleteBuffers(1, ctypes.byref(vbo))
        gl.glDeleteVertexArrays(1, ctypes.byref(vao))

    def _vertex_data_for_model(self, model: Model3D) -> list[float]:
        data: list[float] = []
        for mesh in model.meshes:
            has_face_texcoords = len(mesh.texcoords) == len(mesh.vertices)
            for face in mesh.faces:
                triangles = _triangulate(face)
                if not triangles:
                    continue
                for ia, ib, ic in triangles:
                    for index in (ia, ib, ic):
                        vertex = mesh.vertices[index]
                        if has_face_texcoords:
                            u, v = mesh.texcoords[index]
                        else:
                            u, v = 0.0, 0.0
                        data.extend((vertex.x, vertex.y, vertex.z, u, v))
        return data

    def _program_for_shader(self, shader: Shader3D) -> int:
        key = id(shader)
        if key in self._shader_programs:
            return self._shader_programs[key]
        pyglet = self._load_pyglet()
        gl = pyglet.gl
        vertex_shader = self._compile_shader(
            gl, gl.GL_VERTEX_SHADER, shader.vertex_source, shader.vertex_path
        )
        fragment_shader = self._compile_shader(
            gl, gl.GL_FRAGMENT_SHADER, shader.fragment_source, shader.fragment_path
        )
        program = gl.glCreateProgram()
        gl.glAttachShader(program, vertex_shader)
        gl.glAttachShader(program, fragment_shader)
        gl.glLinkProgram(program)
        status = ctypes.c_int()
        gl.glGetProgramiv(program, gl.GL_LINK_STATUS, ctypes.byref(status))
        if status.value != gl.GL_TRUE:
            raise ShaderCompilationError(
                _link_error_message(gl, program, backend="pyglet", shader=shader)
            )
        self._shader_programs[key] = int(program)
        return int(program)

    def _compile_shader(self, gl: Any, shader_type: int, source: str, path: object) -> int:
        shader = gl.glCreateShader(shader_type)
        encoded = source.encode("utf-8")
        source_buffer = ctypes.c_char_p(encoded)
        source_ptr = ctypes.cast(
            ctypes.pointer(source_buffer), ctypes.POINTER(ctypes.POINTER(ctypes.c_char))
        )
        length = ctypes.c_int(len(encoded))
        gl.glShaderSource(shader, 1, source_ptr, ctypes.byref(length))
        gl.glCompileShader(shader)
        status = ctypes.c_int()
        gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS, ctypes.byref(status))
        if status.value != gl.GL_TRUE:
            stage = "vertex" if shader_type == gl.GL_VERTEX_SHADER else "fragment"
            raise ShaderCompilationError(
                _compile_error_message(gl, shader, backend="pyglet", stage=stage, path=path)
            )
        return int(shader)

    def _apply_builtin_uniforms(
        self,
        gl: Any,
        program: int,
        projection: tuple[tuple[float, ...], ...],
        view: tuple[tuple[float, ...], ...],
        mvp: tuple[tuple[float, ...], ...],
    ) -> None:
        for name, matrix in {
            "u_projection": projection,
            "u_view": view,
            "u_model": _identity4(),
            "u_model_view_projection": mvp,
        }.items():
            with_context = _uniform_location(gl, program, name)
            if with_context >= 0:
                gl.glUniformMatrix4fv(
                    with_context,
                    1,
                    gl.GL_FALSE,
                    (ctypes.c_float * 16)(*_flatten_column_major(matrix)),
                )

    def _apply_material_uniforms(self, gl: Any, program: int, material: Material3D | None) -> None:
        color = (1.0, 1.0, 1.0, 1.0) if material is None else material.base_color
        location = _uniform_location(gl, program, "u_color")
        if location >= 0:
            gl.glUniform4f(location, color[0], color[1], color[2], color[3])

    def _bind_material_texture(
        self,
        gl: Any,
        program: int,
        material: Material3D | None,
        texture: Texture3D | None,
    ) -> bool:
        candidate = texture or (material.texture if material is not None else None)
        use_texture = candidate is not None and isinstance(candidate.source, Image)
        gl.glActiveTexture(gl.GL_TEXTURE0)
        if use_texture:
            assert candidate is not None
            source = candidate.source
            assert isinstance(source, Image)
            texture_id = self._upload_image_texture(gl, source)
            gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        else:
            gl.glBindTexture(gl.GL_TEXTURE_2D, self._fallback_texture(gl))
        location = _uniform_location(gl, program, "u_use_texture")
        if location >= 0:
            gl.glUniform1i(location, 1 if use_texture else 0)
        location = _uniform_location(gl, program, "u_texture")
        if location >= 0:
            gl.glUniform1i(location, 0)
        return use_texture

    def _upload_image_texture(self, gl: Any, image: Image) -> int:
        texture_id = ctypes.c_uint()
        gl.glGenTextures(1, ctypes.byref(texture_id))
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id.value)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        rgba = image.pillow.convert("RGBA")
        data = rgba.tobytes()
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_RGBA,
            rgba.width,
            rgba.height,
            0,
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            data,
        )
        return int(texture_id.value)

    def _fallback_texture(self, gl: Any) -> int:
        if self._fallback_texture_id is not None:
            return self._fallback_texture_id
        texture_id = ctypes.c_uint()
        gl.glGenTextures(1, ctypes.byref(texture_id))
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id.value)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        data = bytes((255, 255, 255, 255))
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_RGBA,
            1,
            1,
            0,
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            data,
        )
        self._fallback_texture_id = int(texture_id.value)
        return self._fallback_texture_id

    def _apply_uniform(self, gl: Any, program: int, name: str, value: ShaderUniformValue) -> None:
        location = _uniform_location(gl, program, name)
        if location < 0:
            return
        if isinstance(value, bool):
            gl.glUniform1i(location, 1 if value else 0)
            return
        if isinstance(value, int):
            gl.glUniform1i(location, value)
            return
        if isinstance(value, float):
            gl.glUniform1f(location, value)
            return
        if isinstance(value, Vec3):
            gl.glUniform3f(location, value.x, value.y, value.z)
            return
        if isinstance(value, Texture3D):
            self._bind_material_texture(gl, program, None, value)
            gl.glUniform1i(location, 0)
            return
        if (
            isinstance(value, tuple)
            and value
            and all(isinstance(item, int | float) for item in value)
        ):
            scalar_items = cast(tuple[int | float, ...], value)
            floats = tuple(float(item) for item in scalar_items)
            if len(floats) == 2:
                gl.glUniform2f(location, floats[0], floats[1])
                return
            if len(floats) == 3:
                gl.glUniform3f(location, floats[0], floats[1], floats[2])
                return
            if len(floats) == 4:
                gl.glUniform4f(location, floats[0], floats[1], floats[2], floats[3])
                return
        if isinstance(value, tuple) and value and all(isinstance(row, tuple) for row in value):
            rows = cast(tuple[tuple[float, ...], ...], value)
            if len(rows) == 2 and all(len(row) == 2 for row in rows):
                gl.glUniformMatrix2fv(
                    location,
                    1,
                    gl.GL_FALSE,
                    (ctypes.c_float * 4)(rows[0][0], rows[1][0], rows[0][1], rows[1][1]),
                )
                return
            if len(rows) == 3 and all(len(row) == 3 for row in rows):
                flattened = tuple(rows[row][col] for col in range(3) for row in range(3))
                gl.glUniformMatrix3fv(location, 1, gl.GL_FALSE, (ctypes.c_float * 9)(*flattened))
                return
            if len(rows) == 4 and all(len(row) == 4 for row in rows):
                gl.glUniformMatrix4fv(
                    location,
                    1,
                    gl.GL_FALSE,
                    (ctypes.c_float * 16)(*_flatten_column_major(rows)),
                )
                return
        raise ShaderUniformError(
            f"Unsupported uniform value for {name!r} on backend 'pyglet': {type(value).__name__}."
        )


def _identity4() -> tuple[tuple[float, ...], ...]:
    return (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def _view_matrix(camera: Camera3D) -> tuple[tuple[float, ...], ...]:
    forward = _normalize(_subtract(camera.target, camera.eye))
    side = _normalize(_cross(forward, camera.up))
    up = _cross(side, forward)
    return (
        (side.x, side.y, side.z, -_dot(side, camera.eye)),
        (up.x, up.y, up.z, -_dot(up, camera.eye)),
        (-forward.x, -forward.y, -forward.z, _dot(forward, camera.eye)),
        (0.0, 0.0, 0.0, 1.0),
    )


def _projection_matrix(
    projection: Projection3D,
    width: int,
    height: int,
) -> tuple[tuple[float, ...], ...]:
    if isinstance(projection, PerspectiveProjection):
        fov = math.radians(projection.fov_y)
        aspect = projection.aspect or (width / max(1, height))
        f = 1.0 / math.tan(fov / 2.0)
        near = projection.near
        far = projection.far
        return (
            (f / aspect, 0.0, 0.0, 0.0),
            (0.0, f, 0.0, 0.0),
            (0.0, 0.0, (far + near) / (near - far), (2 * far * near) / (near - far)),
            (0.0, 0.0, -1.0, 0.0),
        )
    half_width = projection.width / 2.0
    half_height = projection.height / 2.0
    near = projection.near
    far = projection.far
    return (
        (1.0 / max(1e-6, half_width), 0.0, 0.0, 0.0),
        (0.0, 1.0 / max(1e-6, half_height), 0.0, 0.0),
        (0.0, 0.0, -2.0 / max(1e-6, far - near), -(far + near) / max(1e-6, far - near)),
        (0.0, 0.0, 0.0, 1.0),
    )


def _shader_log(gl: Any, shader: int) -> str:
    length = ctypes.c_int()
    gl.glGetShaderiv(shader, gl.GL_INFO_LOG_LENGTH, ctypes.byref(length))
    if length.value <= 1:
        return "Unknown shader compile failure."
    buffer = ctypes.create_string_buffer(length.value)
    gl.glGetShaderInfoLog(shader, length.value, None, buffer)
    return buffer.value.decode("utf-8", errors="replace").strip()


def _program_log(gl: Any, program: int) -> str:
    length = ctypes.c_int()
    gl.glGetProgramiv(program, gl.GL_INFO_LOG_LENGTH, ctypes.byref(length))
    if length.value <= 1:
        return "Unknown shader link failure."
    buffer = ctypes.create_string_buffer(length.value)
    gl.glGetProgramInfoLog(program, length.value, None, buffer)
    return buffer.value.decode("utf-8", errors="replace").strip()


def _compile_error_message(gl: Any, shader: int, *, backend: str, stage: str, path: object) -> str:
    location = f" path={path!s}" if path is not None else ""
    return (
        f"Shader compilation failed on backend {backend!r} "
        f"for {stage} shader.{location}\n{_shader_log(gl, shader)}"
    )


def _link_error_message(gl: Any, program: int, *, backend: str, shader: Shader3D) -> str:
    locations: list[str] = []
    if shader.vertex_path is not None:
        locations.append(f"vertex={shader.vertex_path!s}")
    if shader.fragment_path is not None:
        locations.append(f"fragment={shader.fragment_path!s}")
    location = f" ({', '.join(locations)})" if locations else ""
    return f"Shader link failed on backend {backend!r}{location}\n{_program_log(gl, program)}"


def _uniform_location(gl: Any, program: int, name: str) -> int:
    return int(gl.glGetUniformLocation(program, name.encode("utf-8")))
