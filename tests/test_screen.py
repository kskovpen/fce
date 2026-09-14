import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.screen import screen_size, fit_window


def test_fit_window_shrinks_to_screen():
    assert fit_window(1440, 920, (1440, 900)) == (1440, 800)
    assert fit_window(1440, 920, (1920, 1200)) == (1440, 920)
    assert fit_window(1440, 920, (1280, 800)) == (1280, 700)
    assert fit_window(1440, 920, None) == (1440, 920)


def test_screen_size_is_none_or_positive():
    size = screen_size()
    assert size is None or (size[0] > 0 and size[1] > 0)
