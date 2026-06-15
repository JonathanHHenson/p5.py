"""Backend-neutral sound loading and playback helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from p5.exceptions import ArgumentValidationError, BackendCapabilityError


class Sound:
    """Loaded sound asset with simple playback controls.

    The first milestone uses ``pyglet.media`` under the hood but keeps the public
    object backend-neutral and lazily creates players so loading does not require an
    audio device.
    """

    def __init__(self, source: object, *, path: Path, pyglet_module: Any) -> None:
        self._source = source
        self._path = path
        self._pyglet = pyglet_module
        self._player: Any | None = None
        self._volume = 1.0
        self._rate = 1.0
        self._pan = 0.0

    @property
    def path(self) -> Path:
        return self._path

    @property
    def duration(self) -> float | None:
        duration = getattr(self._source, "duration", None)
        return None if duration is None else float(duration)

    def play(self) -> None:
        self.stop()
        player = self._create_player()
        self._queue_source(player)
        self._apply_controls(player)
        try:
            player.play()
        except Exception as exc:  # pragma: no cover - backend-specific failure path
            self._dispose_player(player)
            raise BackendCapabilityError(
                f"Audio playback is unavailable on this system. Could not play {self._path!s}."
            ) from exc
        self._player = player

    def pause(self) -> None:
        if self._player is None:
            return
        pause = getattr(self._player, "pause", None)
        if callable(pause):
            pause()

    def stop(self) -> None:
        player = self._player
        if player is None:
            return
        pause = getattr(player, "pause", None)
        if callable(pause):
            pause()
        seek = getattr(player, "seek", None)
        if callable(seek):
            seek(0.0)
        self._dispose_player(player)
        self._player = None

    def volume(self, value: float | None = None) -> float:
        if value is not None:
            if value < 0:
                raise ArgumentValidationError("Sound.volume() cannot be negative.")
            self._volume = float(value)
            if self._player is not None:
                self._player.volume = self._volume
        return self._volume

    def rate(self, value: float | None = None) -> float:
        if value is not None:
            if value <= 0:
                raise ArgumentValidationError("Sound.rate() must be positive.")
            self._rate = float(value)
            if self._player is not None:
                self._player.pitch = self._rate
        return self._rate

    def pan(self, value: float | None = None) -> float:
        if value is not None:
            if not -1.0 <= value <= 1.0:
                raise ArgumentValidationError("Sound.pan() must be between -1 and 1.")
            self._pan = float(value)
            if self._player is not None:
                self._player.position = (self._pan, 0.0, 0.0)
        return self._pan

    def _create_player(self) -> Any:
        media = getattr(self._pyglet, "media", self._pyglet)
        player_class = getattr(media, "Player", None)
        if player_class is None:
            raise BackendCapabilityError("pyglet.media Player support is unavailable.")
        try:
            return player_class()
        except Exception as exc:  # pragma: no cover - backend-specific failure path
            raise BackendCapabilityError(
                "Audio playback is unavailable on this system. Could not create a sound player."
            ) from exc

    def _queue_source(self, player: Any) -> None:
        queue = getattr(player, "queue", None)
        if not callable(queue):
            raise BackendCapabilityError("pyglet.media Player.queue() is unavailable.")
        queue(self._source)

    def _apply_controls(self, player: Any) -> None:
        player.volume = self._volume
        player.pitch = self._rate
        player.position = (self._pan, 0.0, 0.0)

    def _dispose_player(self, player: Any) -> None:
        delete = getattr(player, "delete", None)
        if callable(delete):
            delete()


def load_sound(path: str | Path) -> Sound:
    sound_path = Path(path)
    if not sound_path.exists():
        raise ArgumentValidationError(f"Sound file does not exist: {sound_path!s}.")
    pyglet = _load_pyglet_module()
    media = getattr(pyglet, "media", pyglet)
    load = getattr(media, "load", None)
    if not callable(load):
        raise BackendCapabilityError("pyglet.media.load() is unavailable.")
    try:
        source = load(str(sound_path), streaming=False)
    except Exception as exc:
        raise ArgumentValidationError(f"Could not load sound {sound_path!s}.") from exc
    return Sound(source, path=sound_path, pyglet_module=pyglet)


def _load_pyglet_module() -> Any:
    import pyglet

    return pyglet


__all__ = ["Sound", "load_sound"]
