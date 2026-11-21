import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dubzar.performance import PROFILES, profile_for
from dubzar.settings import Settings


def test_light_is_the_mode_the_app_always_had_and_each_step_looks_more_often():
    light, medium, high = (profile_for(name) for name in ("light", "medium", "high"))

    assert (light.poll_s, light.idle_poll_s, light.ocr_threads, light.gpu_ocr) == (0.12, 0.3, 4, False)
    assert light.poll_s > medium.poll_s > high.poll_s
    assert light.idle_poll_s > medium.idle_poll_s > high.idle_poll_s
    assert high.gpu_ocr and not medium.gpu_ocr


def test_every_profile_has_a_turkish_name_and_an_honest_hint():
    for profile in PROFILES.values():
        assert profile.label and profile.hint
    assert "ekran kartı" in profile_for("high").hint


def test_the_setting_accepts_the_three_modes_and_nothing_else():
    settings = Settings()
    assert settings.performance == "light"
    settings.performance = "high"
    assert settings.performance == "high"
    with pytest.raises(ValueError):
        settings.performance = "turbo"


def test_the_panel_controller_cycles_through_the_modes():
    from PySide6.QtWidgets import QApplication

    from dubzar.ui.controller import SettingsController

    QApplication.instance() or QApplication([])
    settings = Settings()
    controller = SettingsController(settings)

    seen = [settings.performance]
    for _ in range(3):
        controller.cyclePerformance()
        seen.append(settings.performance)

    assert seen == ["light", "medium", "high", "light"]
    assert controller.performanceLabel == "Hafif" and controller.performanceHint
