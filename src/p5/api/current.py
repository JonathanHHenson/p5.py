"""Active sketch context management for global mode."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, cast

from p5.exceptions import ContextError

if TYPE_CHECKING:
    from p5.context import SketchContext

_ACTIVE_CONTEXT: ContextVar[object | None] = ContextVar("p5_active_context", default=None)


def get_active_context() -> SketchContext | None:
    return cast("SketchContext | None", _ACTIVE_CONTEXT.get())


def require_context() -> SketchContext:
    context = get_active_context()
    if context is None:
        raise ContextError(
            "This p5-py API requires an active sketch. "
            "Call it from setup(), draw(), or run a Sketch."
        )
    return context


@contextmanager
def activate_context(context: object) -> Iterator[None]:
    token = _ACTIVE_CONTEXT.set(context)
    try:
        yield
    finally:
        _ACTIVE_CONTEXT.reset(token)
