def health_check() -> str: ...
def noise3(
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    seed: int = 0,
    octaves: int = 4,
    falloff: float = 0.5,
) -> float: ...
def exclusion_blend_rgb(base: bytes, overlay: bytes) -> bytes: ...
