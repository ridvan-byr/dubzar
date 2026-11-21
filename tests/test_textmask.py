import numpy as np

from dubzar.textmask import TextChangeWatcher, mask_distance, text_mask


def scene(seed=0, brightness=50):
    """A dark moving-looking picture: random low-contrast noise."""
    rng = np.random.default_rng(seed)
    return np.clip(brightness + rng.integers(-6, 7, (330, 1200, 3)), 0, 255).astype(np.uint8)


def with_subtitle(frame, x0=300, x1=900, y0=200, period=12):
    """Bright letter-like strokes with a dark outline, as a game draws a subtitle."""
    frame = frame.copy()
    for k, offset in enumerate(range(x0, x1, period)):
        height = 26 if k % 3 else 34
        frame[y0 - 2: y0 + height + 2, offset - 2: offset + 6] = 0           # the outline
        frame[y0: y0 + height, offset: offset + 3] = 255                      # the stroke
    return frame


def test_a_subtitle_makes_a_mask_and_a_plain_scene_does_not():
    assert text_mask(with_subtitle(scene())).sum() > 200
    assert text_mask(scene()).sum() < 20


def test_distance_is_zero_for_the_same_mask_and_large_for_different_ones():
    a = text_mask(with_subtitle(scene()))
    b = text_mask(with_subtitle(scene(), x0=307, y0=120, period=9))

    assert mask_distance(a, a) == 0.0
    assert mask_distance(a, b) > 0.6
    assert mask_distance(np.zeros_like(a), np.zeros_like(a)) == 0.0


def test_a_new_subtitle_is_noticed_and_a_static_one_is_not_noticed_again():
    watcher = TextChangeWatcher()
    assert not watcher.changed(scene(1))                          # nothing yet
    watcher.commit()

    assert watcher.changed(with_subtitle(scene(2)))               # it appears
    watcher.commit()
    assert not watcher.changed(with_subtitle(scene(3)))           # same text, a different moving background
    assert not watcher.changed(with_subtitle(scene(4)))


def test_a_different_subtitle_in_the_same_place_is_noticed():
    watcher = TextChangeWatcher()
    watcher.changed(with_subtitle(scene(1)))
    watcher.commit()

    assert watcher.changed(with_subtitle(scene(2), x0=307, x1=840, period=9))   # other letters, other spacing


def test_a_subtitle_going_away_is_noticed():
    watcher = TextChangeWatcher()
    watcher.changed(with_subtitle(scene(1)))
    watcher.commit()

    assert watcher.changed(scene(2))


def test_the_reference_only_moves_when_committed():
    watcher = TextChangeWatcher()
    watcher.changed(with_subtitle(scene(1)))                      # seen but not read yet

    assert watcher.changed(with_subtitle(scene(2)))               # still "new": nothing was committed
