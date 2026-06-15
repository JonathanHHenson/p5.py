from pathlib import Path

import p5
from p5.assets import sound as sound_module


class _FakeSource:
    duration = 1.25


class _FakePlayer:
    def __init__(self) -> None:
        self.queued = []
        self.play_calls = 0
        self.pause_calls = 0
        self.seek_calls = []
        self.delete_calls = 0
        self.volume = 0.0
        self.pitch = 0.0
        self.position = (0.0, 0.0, 0.0)

    def queue(self, source) -> None:
        self.queued.append(source)

    def play(self) -> None:
        self.play_calls += 1

    def pause(self) -> None:
        self.pause_calls += 1

    def seek(self, value: float) -> None:
        self.seek_calls.append(value)

    def delete(self) -> None:
        self.delete_calls += 1


class _FakeMedia:
    Player = _FakePlayer
    last_load = None

    @staticmethod
    def load(path: str, *, streaming: bool) -> _FakeSource:
        _FakeMedia.last_load = (path, streaming)
        return _FakeSource()


class _FakePyglet:
    media = _FakeMedia


def test_load_sound_and_create_audio_wrap_pyglet_media(monkeypatch, tmp_path: Path):
    sound_path = tmp_path / "tone.wav"
    sound_path.write_bytes(b"RIFFfakeWAVE")
    monkeypatch.setattr(sound_module, "_load_pyglet_module", lambda: _FakePyglet)

    clip = p5.load_sound(sound_path)
    clip.volume(0.4)
    clip.rate(1.5)
    clip.pan(-0.25)
    clip.play()

    assert clip.duration == 1.25
    assert _FakeMedia.last_load == (str(sound_path), False)
    player = clip._player
    assert player is not None
    assert player.play_calls == 1
    assert player.volume == 0.4
    assert player.pitch == 1.5
    assert player.position == (-0.25, 0.0, 0.0)

    clip.pause()
    clip.stop()

    assert player.pause_calls >= 2
    assert player.seek_calls == [0.0]
    assert player.delete_calls == 1
    assert clip._player is None

    created = p5.create_audio(sound_path)
    assert isinstance(created, sound_module.Sound)
