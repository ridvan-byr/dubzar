"""Per-game settings: a game can have its own subtitle look (size, position, colours), speed mode and screen.

The settings object always holds the values in use. Outside a game profile they are the base values; while a game with a
profile is in front they are that game's, and a change goes to the profile instead of the base. The base is kept
aside so saving never writes one game's look as everyone's.
"""

from typing import Callable, Iterable

from dubzar.settings import PROFILE_KEYS, Settings

# programs that are never the game: the desktop, our own windows and the usual helpers
IGNORED_PROCESSES = frozenset({
    "explorer.exe", "python.exe", "pythonw.exe", "dubzar.exe", "dwm.exe", "taskmgr.exe", "searchhost.exe",
    "applicationframehost.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe", "textinputhost.exe",
})


def game_for(process: str | None, fullscreen: bool, known: Iterable[str], ignored=IGNORED_PROCESSES) -> str | None:
    """The game in front, or None when nothing in front looks like one: a program with a profile, or any program
    that fills the screen (apart from the usual desktop programs)."""
    if not process:
        return None
    name = process.lower()
    if name in known:
        return name
    return name if fullscreen and name not in ignored else None


class ProfileManager:
    def __init__(self, settings: Settings):
        self._s = settings
        self.active: str | None = None
        self._applying = False
        self._listeners: list[Callable[[], None]] = []
        self.base = {key: getattr(settings, key) for key in PROFILE_KEYS}
        settings.attach_base(self.base)
        settings.on_change(self._changed)

    def on_change(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    @property
    def profiles(self) -> dict[str, dict]:
        return self._s.profiles

    @property
    def is_on(self) -> bool:
        """The game in front has a profile of its own."""
        return self.active is not None and self.active in self.profiles

    def set_game(self, game: str | None) -> None:
        game = game.lower() if game else None
        if game == self.active:
            return
        self.active = game
        self._apply()
        self._notify()

    def set_on(self, on: bool) -> None:
        """Give the game in front its own settings (starting from what is in use now), or take them away again."""
        if self.active is None or on == self.is_on:
            return
        if on:
            self.profiles[self.active] = {key: getattr(self._s, key) for key in PROFILE_KEYS}
        else:
            del self.profiles[self.active]
            self._apply()
        self._s.changed_profiles()
        self._notify()

    def _apply(self) -> None:
        values = dict(self.base)
        if self.is_on:
            values.update(self.profiles[self.active])
        self._applying = True
        try:
            for key, value in values.items():
                setattr(self._s, key, value)
        finally:
            self._applying = False

    def _changed(self, name: str) -> None:
        if self._applying or name not in PROFILE_KEYS:
            return
        value = getattr(self._s, name)
        if self.is_on:
            self.profiles[self.active][name] = value
        else:
            self.base[name] = value

    def _notify(self) -> None:
        for callback in list(self._listeners):
            callback()


class GameTracker:
    """Called every second or two: tells the manager which game is in front. A game stays "the game" while its
    process runs, also when another window (the desktop, this panel's neighbours) is in front for a moment."""

    def __init__(self, manager: ProfileManager, foreground: Callable[[], tuple[str | None, bool]],
                 is_running: Callable[[str], bool], configured: Callable[[], str | None] = lambda: None):
        self._manager = manager
        self._foreground = foreground
        self._is_running = is_running
        self._configured = configured

    def tick(self) -> None:
        configured = self._configured()
        if configured:
            game = configured.lower() if self._is_running(configured) else None
        else:
            process, fullscreen = self._foreground()
            game = game_for(process, fullscreen, self._manager.profiles.keys())
            current = self._manager.active
            if game is None and current and self._is_running(current):
                game = current
        self._manager.set_game(game)
