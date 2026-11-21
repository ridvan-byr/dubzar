import numpy as np

from dubzar.textmask import TextChangeWatcher, mask_distance, text_mask


def scene(seed=0, brightness=50):
    """A dark picture with low-contrast noise."""
    rng = np.random.default_rng(seed)
    return np.clip(brightness + rng.integers(-6, 7, (330, 1200, 3)), 0, 255).astype(np.uint8)


def moving_scene(seed, n_blobs=14):
    """A busy game scene whose bright, dark-edged shapes are somewhere else on every look (a panning camera)."""
    rng = np.random.default_rng(seed)
    frame = scene(seed)
    for _ in range(n_blobs):
        x, y = int(rng.integers(20, 1100)), int(rng.integers(10, 280))
        frame[y - 3: y + 28, x - 3: x + 10] = 0
        frame[y: y + 25, x: x + 5] = 255
    return frame


def with_subtitle(frame, x0=300, x1=900, y0=200, period=12):
    """Bright letter-like strokes with a dark outline, as a game draws a subtitle."""
    frame = frame.copy()
    for k, offset in enumerate(range(x0, x1, period)):
        height = 26 if k % 3 else 34
        frame[y0 - 2: y0 + height + 2, offset - 2: offset + 6] = 0           # the outline
        frame[y0: y0 + height, offset: offset + 3] = 255                      # the stroke
    return frame


def look(watcher, frame, commit=True):
    """One look at the strip; a reading (commit) follows when the watcher says it changed."""
    changed = watcher.changed(frame)
    if changed and commit:
        watcher.commit()
    return changed


def test_a_subtitle_makes_a_mask_and_a_plain_scene_does_not():
    assert text_mask(with_subtitle(scene())).sum() > 200
    assert text_mask(scene()).sum() < 20


def test_distance_is_zero_for_the_same_mask_and_large_for_different_ones():
    a = text_mask(with_subtitle(scene()))
    b = text_mask(with_subtitle(scene(), x0=307, y0=120, period=9))

    assert mask_distance(a, a) == 0.0
    assert mask_distance(a, b) > 0.6
    assert mask_distance(np.zeros_like(a), np.zeros_like(a)) == 0.0


def test_a_subtitle_is_noticed_once_it_has_stayed_put_for_two_looks_and_then_not_again():
    watcher = TextChangeWatcher()
    assert not look(watcher, scene(1)) and not look(watcher, scene(2))        # nothing on screen

    assert not look(watcher, with_subtitle(scene(3)))                         # first look at it: may be passing
    assert look(watcher, with_subtitle(scene(4)))                             # still there: a subtitle
    assert not look(watcher, with_subtitle(scene(5)))                         # the same one, another background
    assert not look(watcher, with_subtitle(scene(6)))


def test_a_busy_moving_scene_without_subtitles_does_not_raise_alarms():
    """In a game the camera never stops: bright, outlined shapes are different on every look. They are not subtitles."""
    watcher = TextChangeWatcher()

    alarms = sum(look(watcher, moving_scene(seed)) for seed in range(40))

    assert alarms <= 2


def test_a_subtitle_is_still_noticed_over_a_busy_moving_scene():
    watcher = TextChangeWatcher()
    for seed in range(5):
        look(watcher, moving_scene(seed))

    first = look(watcher, with_subtitle(moving_scene(10)))
    second = look(watcher, with_subtitle(moving_scene(11)))                   # the scene moved, the subtitle did not

    assert second and not first


def test_a_different_subtitle_in_the_same_place_is_noticed():
    watcher = TextChangeWatcher()
    look(watcher, with_subtitle(scene(1)))
    look(watcher, with_subtitle(scene(2)))

    look(watcher, with_subtitle(scene(3), x0=307, x1=840, period=9))
    assert look(watcher, with_subtitle(scene(4), x0=307, x1=840, period=9))   # other letters, other spacing


def test_a_subtitle_going_away_is_noticed():
    watcher = TextChangeWatcher()
    look(watcher, with_subtitle(scene(1)))
    look(watcher, with_subtitle(scene(2)))

    look(watcher, scene(3))
    assert look(watcher, scene(4))


def test_the_reference_only_moves_when_committed():
    watcher = TextChangeWatcher()
    look(watcher, with_subtitle(scene(1)))
    assert look(watcher, with_subtitle(scene(2)), commit=False)               # seen but not read yet

    assert look(watcher, with_subtitle(scene(3)), commit=False)               # still "new": nothing was committed


def test_a_subtitle_just_appearing_asks_for_a_quick_second_look_but_a_moving_scene_does_not():
    watcher = TextChangeWatcher()
    look(watcher, scene(1))
    look(watcher, scene(2))
    look(watcher, with_subtitle(scene(3)))
    assert watcher.settling                                                   # calm, then text: look again at once

    busy = TextChangeWatcher()
    for seed in range(6):
        look(busy, moving_scene(seed))
    assert not busy.settling                                                  # never calm: no extra looks
