import numpy as np
import pytest

from dubzar import imageprep


def frame_with_text_like_block(bg=40, fg=255, outline=True):
    """A dark scene with a bright 'letter' block that has a dark outline around it."""
    image = np.full((60, 200, 3), bg, dtype=np.uint8)
    if outline:
        image[18:42, 58:142] = 0
    image[22:38, 62:138] = fg
    return image


def test_upscaling_doubles_the_size():
    out = imageprep.upscale(frame_with_text_like_block(), 2)

    assert out.shape[:2] == (120, 400) and out.dtype == np.uint8


def test_bright_text_becomes_dark_on_white():
    out = imageprep.bright_on_white(frame_with_text_like_block())

    assert out.shape[:2] == (120, 400)                  # also enlarged: small glyphs read better
    assert out[60, 200].mean() < 60                     # the bright block is black now
    assert out[5, 5].mean() > 200                       # the dark scene is white


def test_bright_scene_areas_without_an_outline_are_dropped_by_the_outline_variant():
    scene = np.full((60, 200, 3), 40, dtype=np.uint8)
    scene[5:55, 5:60] = 250                             # a big bright wall: no dark outline inside it
    for x in range(100, 180, 8):                        # letter strokes: 3 px wide, bright, with a dark outline
        scene[19:41, x - 2:x + 5] = 0
        scene[21:39, x:x + 3] = 255

    out = imageprep.outlined_on_white(scene)

    assert out[2 * 30, 2 * 30].mean() > 200             # the middle of the wall is gone (white)
    assert out[2 * 30, 2 * 101 + 1].mean() < 100        # a letter stroke stays (black)


def test_dark_text_on_light_box_becomes_black_on_white():
    image = np.full((60, 200, 3), 235, dtype=np.uint8)
    image[22:38, 62:138] = 20

    out = imageprep.dark_on_white(image)

    assert out[60, 200].mean() < 60 and out[5, 5].mean() > 200


def test_variants_come_cheapest_first_and_are_all_images():
    names_and_images = list(imageprep.variants(frame_with_text_like_block()))

    assert names_and_images[0][0] == "x2"                # the best single reading goes first
    assert len({n for n, _ in names_and_images}) == len(names_and_images) >= 5
    for _, image in names_and_images:
        assert image.ndim == 3 and image.shape[2] == 3 and image.dtype == np.uint8
