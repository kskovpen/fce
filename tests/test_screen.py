import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.screen import screen_size, fit_window, parse_xrandr

_XRANDR = """\
Screen 0: minimum 320 x 200, current 4800 x 1800, maximum 16384 x 16384
eDP-1 connected primary 2880x1800+0+0 (normal left inverted right x axis y axis) 302mm x 189mm
   2880x1800     60.00*+
HDMI-1 connected 1920x1080+2880+0 (normal left inverted right x axis y axis) 527mm x 296mm
DP-1 disconnected (normal left inverted right x axis y axis)
"""


def test_parse_xrandr_prefers_primary_output():
    assert parse_xrandr(_XRANDR) == (2880, 1800)


def test_parse_xrandr_without_primary_uses_first_active_output():
    text = _XRANDR.replace(" primary", "").replace(
        "eDP-1 connected 2880x1800+0+0", "eDP-1 connected (normal left)")
    assert parse_xrandr(text) == (1920, 1080)
    assert parse_xrandr("Screen 0: minimum 8 x 8\nXWAYLAND0 disconnected\n") is None


def test_parse_xrandr_xwayland():
    text = "Screen 0: current 3840 x 2160\nXWAYLAND0 connected 3840x2160+0+0 0mm x 0mm\n"
    assert parse_xrandr(text) == (3840, 2160)


def test_fit_window_shrinks_to_screen():
    assert fit_window(1440, 920, (1440, 900)) == (1440, 800)
    assert fit_window(1440, 920, (1920, 1200)) == (1440, 920)
    assert fit_window(2880, 1840, (2880, 1800)) == (2880, 1700)
    assert fit_window(1440, 920, None) == (1440, 920)


def test_screen_size_is_none_or_positive():
    size = screen_size()
    assert size is None or (size[0] > 0 and size[1] > 0)
