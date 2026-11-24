import sys

import numpy as np
import pytest

from dubzar import screen


def test_an_empty_or_reversed_box_is_not_grabbed_by_gdi():
    assert screen._grab_region((10, 10, 10, 50)) is None
    assert screen._grab_region((50, 50, 10, 10)) is None


@pytest.mark.skipif(sys.platform != "win32", reason="GDI screen copy")
def test_a_region_comes_back_as_rgb_rows_of_the_asked_size():
    picture = screen.grab((0, 0, 64, 32))
    assert picture.shape == (32, 64, 3) and picture.dtype == np.uint8


def test_the_shared_reader_can_swap_its_engine_while_it_runs():
    from dubzar.app import _SharedReader

    class Reader:
        def __init__(self, language):
            self.language = language

        def read(self, image):
            return self.language

    shared = _SharedReader(Reader("cpu"))
    assert shared.read(None) == "cpu"
    shared.replace(Reader("gpu"))
    assert shared.read(None) == "gpu" and shared.language == "gpu"
