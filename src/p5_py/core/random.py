"""Seedable p5-style random and Perlin noise helpers."""

from __future__ import annotations

import math
import random as _random
from collections.abc import Sequence
from typing import cast

Number = int | float

_random_generator = _random.Random()
_noise_seed = 0
_noise_octaves = 4
_noise_falloff = 0.5


def random_seed(seed: int | float | str | bytes | bytearray | None) -> None:
    _random_generator.seed(seed)


def random(*args: object):
    if len(args) == 0:
        return _random_generator.random()
    if len(args) == 1:
        value = args[0]
        if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
            if len(value) == 0:
                return None
            return _random_generator.choice(value)
        if not isinstance(value, int | float):
            raise TypeError("random(max) requires a numeric max value or a non-string sequence.")
        return _random_generator.random() * float(value)
    if len(args) == 2:
        if not all(isinstance(arg, int | float) for arg in args):
            raise TypeError("random(low, high) requires numeric bounds.")
        low, high = cast(tuple[Number, Number], args)
        low, high = float(low), float(high)
        return _random_generator.uniform(low, high)
    msg = "random() accepts zero arguments, a max value/list, or low and high values."
    raise TypeError(msg)


def random_gaussian(mean: Number = 0, sd: Number = 1) -> float:
    return _random_generator.gauss(float(mean), float(sd))


def noise_seed(seed: int) -> None:
    global _noise_seed
    _noise_seed = int(seed)


def noise_detail(octaves: int, falloff: Number | None = None) -> None:
    global _noise_octaves, _noise_falloff
    if octaves < 1:
        msg = "noise_detail() octave count must be at least 1."
        raise ValueError(msg)
    _noise_octaves = int(octaves)
    if falloff is not None:
        _noise_falloff = float(falloff)


def noise(x: Number = 0, y: Number = 0, z: Number = 0) -> float:
    total = 0.0
    amplitude = 1.0
    max_amplitude = 0.0
    frequency = 1.0
    for _ in range(_noise_octaves):
        total += (
            _perlin(float(x) * frequency, float(y) * frequency, float(z) * frequency) * amplitude
        )
        max_amplitude += amplitude
        amplitude *= _noise_falloff
        frequency *= 2.0
    return total / max_amplitude if max_amplitude else 0.0


def _perlin(x: float, y: float, z: float) -> float:
    x0 = math.floor(x)
    y0 = math.floor(y)
    z0 = math.floor(z)
    xf = x - x0
    yf = y - y0
    zf = z - z0
    u = _fade(xf)
    v = _fade(yf)
    w = _fade(zf)

    dots = {}
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                gradient = _gradient(x0 + dx, y0 + dy, z0 + dz)
                dots[(dx, dy, dz)] = (
                    gradient[0] * (xf - dx) + gradient[1] * (yf - dy) + gradient[2] * (zf - dz)
                )

    x00 = _lerp(dots[(0, 0, 0)], dots[(1, 0, 0)], u)
    x10 = _lerp(dots[(0, 1, 0)], dots[(1, 1, 0)], u)
    x01 = _lerp(dots[(0, 0, 1)], dots[(1, 0, 1)], u)
    x11 = _lerp(dots[(0, 1, 1)], dots[(1, 1, 1)], u)
    y0_value = _lerp(x00, x10, v)
    y1_value = _lerp(x01, x11, v)
    return (_lerp(y0_value, y1_value, w) + 1.0) / 2.0


def _gradient(x: int, y: int, z: int) -> tuple[float, float, float]:
    hashed = _hash(x, y, z)
    theta = (hashed & 0xFFFF) / 0xFFFF * math.tau
    phi = ((hashed >> 16) & 0xFFFF) / 0xFFFF * math.pi
    sin_phi = math.sin(phi)
    return math.cos(theta) * sin_phi, math.sin(theta) * sin_phi, math.cos(phi)


def _hash(x: int, y: int, z: int) -> int:
    value = (_noise_seed & 0xFFFFFFFF) ^ (x * 374761393) ^ (y * 668265263) ^ (z * 2246822519)
    value = (value ^ (value >> 13)) * 1274126177
    return (value ^ (value >> 16)) & 0xFFFFFFFF


def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


__all__ = ["random", "random_seed", "random_gaussian", "noise", "noise_seed", "noise_detail"]
