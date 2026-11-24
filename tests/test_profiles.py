import json

from dubzar.profiles import GameTracker, ProfileManager, game_for
from dubzar.settings import Settings, load_settings, save_settings


def test_a_program_with_a_profile_or_filling_the_screen_is_the_game():
    assert game_for("GTA5.exe", True, []) == "gta5.exe"
    assert game_for("Chrome.exe", False, ["chrome.exe"]) == "chrome.exe"
    assert game_for("notepad.exe", False, []) is None          # a window, not a game
    assert game_for("explorer.exe", True, []) is None          # the desktop fills the screen too
    assert game_for(None, True, []) is None


def test_without_a_profile_edits_change_the_base_values():
    s = Settings()
    m = ProfileManager(s)
    m.set_game("gta5.exe")

    s.font_size = 40

    assert m.base["font_size"] == 40 and m.profiles == {}


def test_a_profile_starts_from_the_values_in_use_and_takes_later_edits():
    s = Settings(font_size=30)
    m = ProfileManager(s)
    m.set_game("gta5.exe")

    m.set_on(True)
    s.font_size = 44
    s.text_color = "#FFD166"

    assert m.profiles["gta5.exe"]["font_size"] == 44 and m.profiles["gta5.exe"]["text_color"] == "#FFD166"
    assert m.base["font_size"] == 30 and m.base["text_color"] == "#FFFFFF"      # the base did not move


def test_switching_games_swaps_the_values_in_use():
    s = Settings(font_size=30)
    m = ProfileManager(s)
    m.set_game("gta5.exe")
    m.set_on(True)
    s.font_size = 44
    m.set_game("witcher3.exe")

    assert s.font_size == 30                       # a game without a profile gets the base values
    m.set_game("gta5.exe")
    assert s.font_size == 44                       # and the first one gets its own back


def test_turning_a_profile_off_returns_to_the_base_and_forgets_the_values():
    s = Settings(font_size=30)
    m = ProfileManager(s)
    m.set_game("gta5.exe")
    m.set_on(True)
    s.font_size = 44

    m.set_on(False)

    assert s.font_size == 30 and "gta5.exe" not in m.profiles


def test_set_on_without_a_game_does_nothing():
    m = ProfileManager(Settings())

    m.set_on(True)

    assert m.profiles == {} and not m.is_on


def test_saving_writes_the_base_values_and_the_profiles(tmp_path):
    s = Settings(font_size=30)
    m = ProfileManager(s)
    m.set_game("gta5.exe")
    m.set_on(True)
    s.font_size = 44
    path = tmp_path / "settings.json"

    save_settings(s, path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["font_size"] == 30 and data["profiles"]["gta5.exe"]["font_size"] == 44


def test_profiles_survive_a_restart_and_bad_entries_are_dropped(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"font_size": 30, "profiles": {
        "GTA5.exe": {"font_size": 44, "text_color": "red", "hotkey": "Ctrl+Q"},     # a bad colour, a key not allowed
        "not a program": {"font_size": 20}, "x.exe": "nope"}}), encoding="utf-8")

    s = load_settings(path)

    assert s.profiles == {"gta5.exe": {"font_size": 44}}
    assert s.font_size == 30


def test_the_tracker_follows_the_game_and_keeps_it_while_it_runs():
    m = ProfileManager(Settings())
    seen = {"fg": ("GTA5.exe", True), "running": {"gta5.exe"}}
    tracker = GameTracker(m, lambda: seen["fg"], lambda name: name.lower() in seen["running"])

    tracker.tick()
    assert m.active == "gta5.exe"
    seen["fg"] = ("explorer.exe", True)           # alt-tab to the desktop: still the same game
    tracker.tick()
    assert m.active == "gta5.exe"
    seen["running"] = set()                       # the game was closed
    tracker.tick()
    assert m.active is None


def test_a_configured_game_is_the_game_only_while_it_runs():
    m = ProfileManager(Settings())
    running = {"state": True}
    tracker = GameTracker(m, lambda: ("chrome.exe", False), lambda name: running["state"], lambda: "Game.exe")

    tracker.tick()
    assert m.active == "game.exe"
    running["state"] = False
    tracker.tick()
    assert m.active is None


def test_listeners_hear_about_game_and_profile_changes():
    m = ProfileManager(Settings())
    heard = []
    m.on_change(lambda: heard.append(1))

    m.set_game("a.exe")
    m.set_on(True)
    m.set_game("a.exe")

    assert len(heard) == 2                        # the repeat of the same game is no change
