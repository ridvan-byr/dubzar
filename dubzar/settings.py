"""User settings: validated, observable, resettable, saved as JSON."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable

from dubzar.hotkey import parse_hotkey

log = logging.getLogger(__name__)

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _boolean(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"expected true/false, got {value!r}")
    return value


def _hex_color(value: Any) -> str:
    if not isinstance(value, str) or not _HEX.match(value):
        raise ValueError(f"expected a color like #FFD166, got {value!r}")
    return value.upper()


def _int_between(low: int, high: int) -> Callable[[Any], int]:
    def check(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f"expected a whole number from {low} to {high}, got {value!r}")
        return value
    return check


def _float_between(low: float, high: float) -> Callable[[Any], float]:
    def check(value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise ValueError(f"expected a number from {low} to {high}, got {value!r}")
        return float(value)
    return check


def _screen(value: Any) -> str:
    if value in ("auto", "primary") or (isinstance(value, str) and value.isdigit() and int(value) >= 1):
        return value
    raise ValueError(f"screen must be 'auto', 'primary' or a number >= 1, got {value!r}")


def _panel_screen(value: Any) -> str:
    if value == "other":
        return value
    return _screen(value)


def _hotkey(value: Any) -> str:
    parse_hotkey(value)  # raises ValueError when it is not a usable hotkey
    return value


def _performance(value: Any) -> str:
    if value == "medium":      # the middle mode was removed; settings saved with it open as Light
        return "light"
    if value not in ("light", "high"):
        raise ValueError(f"performance must be 'light' or 'high', got {value!r}")
    return value


def _optional_exe_name(value: Any) -> str | None:
    if value is None:
        return None
    if (not isinstance(value, str) or not value.lower().endswith(".exe")
            or "/" in value or chr(92) in value or value.lower() == ".exe"):
        raise ValueError(f"game_exe must be a plain file name like GTA5.exe, got {value!r}")
    return value


# what a game can have of its own (the rest, like the hotkey, stays the same everywhere)
PROFILE_KEYS = ("subtitles_enabled", "font_size", "vertical", "text_color", "background_color",
                "background_opacity", "performance", "screen")

OLD_DEFAULT_HOTKEY = "Ctrl+Shift+D"       # browsers use it (bookmark all tabs); the default is now Ctrl+Alt+D


# name -> (default, validator that returns the normalised value or raises ValueError)
_SPEC: dict[str, tuple[Any, Callable[[Any], Any]]] = {
    "subtitles_enabled": (True, _boolean),
    "dubbing_enabled": (True, _boolean),
    "font_size": (28, _int_between(12, 96)),
    "vertical": (0.80, _float_between(0.0, 1.0)),  # subtitle position: 0 = top, 1 = bottom
    "text_color": ("#FFFFFF", _hex_color),
    "background_color": ("#000000", _hex_color),
    "background_opacity": (60, _int_between(0, 100)),  # percent
    "screen": ("auto", _screen),
    "panel_screen": ("auto", _panel_screen),  # where the settings panel opens; "auto" = the game's screen
    "hotkey": ("Ctrl+Alt+D", _hotkey),
    "performance": ("light", _performance),  # how often the screen is read and by what; see dubzar.performance
    "game_exe": (None, _optional_exe_name),  # the game's process; the background scan waits while it runs
}


class Settings:
    """Plain attributes with validation. A rejected change leaves everything untouched.

    ``on_change(callback)`` registers ``callback(name)``, called whenever a value actually changes.
    """

    def __init__(self, **values: Any):
        object.__setattr__(self, "_callbacks", [])
        object.__setattr__(self, "profiles", {})       # game exe (lower case) -> its own values; see dubzar.profiles
        object.__setattr__(self, "_base", None)       # the values outside any game profile, once profiles are in use
        for name, (default, _) in _SPEC.items():
            object.__setattr__(self, name, default)
        for name, value in values.items():
            setattr(self, name, value)

    def __setattr__(self, name: str, value: Any) -> None:
        if name not in _SPEC:
            raise AttributeError(f"unknown setting {name!r}")
        new = _SPEC[name][1](value)
        if new == getattr(self, name):
            return
        object.__setattr__(self, name, new)
        for callback in list(self._callbacks):
            callback(name)

    def on_change(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    def changed_profiles(self) -> None:
        """Tell the listeners (the saver) that the profiles changed."""
        for callback in list(self._callbacks):
            callback("profiles")

    def attach_base(self, base: dict[str, Any]) -> None:
        """While a game profile is active the live values are that game's; saving writes ``base`` for those keys."""
        object.__setattr__(self, "_base", base)

    def to_save_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        if self._base is not None:
            data.update(self._base)
        data["profiles"] = {game: dict(values) for game, values in self.profiles.items()}
        return data

    def reset(self) -> None:
        for name, (default, _) in _SPEC.items():
            setattr(self, name, default)

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in _SPEC}

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Settings) and self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        return f"Settings({self.to_dict()})"


def default_settings_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "Dubzar" / "settings.json"


def load_settings(path: Path | str | None = None) -> Settings:
    """Read settings; a missing or corrupt file gives defaults, bad entries fall back individually."""
    path = Path(path) if path else default_settings_path()
    settings = Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return settings
    except (OSError, ValueError):
        log.warning("could not read settings file %s, using defaults", path)
        return settings
    if not isinstance(data, dict):
        return settings
    for name in _SPEC:
        if name in data:
            try:
                setattr(settings, name, data[name])
            except ValueError as exc:
                log.warning("ignoring invalid setting %s: %s", name, exc)
    settings.profiles.update(_read_profiles(data.get("profiles")))
    if settings.hotkey == OLD_DEFAULT_HOTKEY:
        settings.hotkey = _SPEC["hotkey"][0]     # saved by an older version: that default clashed with browsers
    return settings


def _read_profiles(raw: Any) -> dict[str, dict[str, Any]]:
    """Per-game values from the file; anything invalid is dropped on its own."""
    profiles: dict[str, dict[str, Any]] = {}
    if not isinstance(raw, dict):
        return profiles
    for game, values in raw.items():
        try:
            game = _optional_exe_name(game)
        except ValueError:
            log.warning("ignoring a profile with a bad game name: %r", game)
            continue
        if game is None or not isinstance(values, dict):
            continue
        clean = {}
        for name, value in values.items():
            if name not in PROFILE_KEYS:
                continue
            try:
                clean[name] = _SPEC[name][1](value)
            except ValueError as exc:
                log.warning("ignoring invalid profile value %s for %s: %s", name, game, exc)
        profiles[game.lower()] = clean
    return profiles


def save_settings(settings: Settings, path: Path | str | None = None) -> None:
    """Write settings atomically (temp file, then rename) so a crash never leaves half a file."""
    path = Path(path) if path else default_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(settings.to_save_dict(), indent=2), encoding="utf-8")
    temp.replace(path)
