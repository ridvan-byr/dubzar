import json

import pytest

from dubzar.settings import Settings, load_settings, save_settings


def test_defaults():
    s = Settings()

    assert (s.subtitles_enabled, s.dubbing_enabled) == (True, True)
    assert (s.font_size, s.text_color, s.background_color, s.background_opacity) == (28, "#FFFFFF", "#000000", 60)
    assert (s.screen, s.hotkey) == ("auto", "Ctrl+Shift+D")
    assert 0.0 <= s.vertical <= 1.0


def test_reset_restores_every_default_in_place():
    s = Settings()
    s.font_size = 40
    s.text_color = "#FFD166"
    s.dubbing_enabled = False
    s.vertical = 0.2

    s.reset()

    assert s == Settings()


@pytest.mark.parametrize("field,value", [
    ("font_size", 0), ("font_size", 300), ("vertical", -0.1), ("vertical", 1.5),
    ("background_opacity", -1), ("background_opacity", 101),
    ("text_color", "red"), ("background_color", "#12"), ("screen", "left"), ("hotkey", "D"),
])
def test_invalid_values_are_rejected(field, value):
    s = Settings()

    with pytest.raises(ValueError):
        setattr(s, field, value)

    assert s == Settings()  # a rejected change leaves the settings untouched


def test_colors_are_normalised_to_upper_case_hex():
    s = Settings()
    s.text_color = "#ffd166"

    assert s.text_color == "#FFD166"


def test_changed_callback_fires_on_change_but_not_when_the_value_is_the_same():
    s = Settings()
    seen: list[str] = []
    s.on_change(seen.append)

    s.font_size = 32
    s.font_size = 32  # unchanged
    s.reset()

    assert seen == ["font_size", "font_size"]  # the change, then the reset back to 28


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    s = Settings()
    s.font_size = 36
    s.dubbing_enabled = False
    s.text_color = "#FFD166"

    save_settings(s, path)
    loaded = load_settings(path)

    assert loaded == s


def test_load_missing_file_gives_defaults(tmp_path):
    assert load_settings(tmp_path / "nope.json") == Settings()


def test_load_ignores_unknown_and_invalid_entries_instead_of_crashing(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"font_size": 999, "text_color": "#FFD166", "future_option": 1}))

    loaded = load_settings(path)

    assert loaded.font_size == 28  # invalid value falls back to the default
    assert loaded.text_color == "#FFD166"  # valid entries are still applied


def test_load_corrupt_file_gives_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json")

    assert load_settings(path) == Settings()
