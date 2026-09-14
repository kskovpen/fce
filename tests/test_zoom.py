import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.zoom import (ZOOM_STEPS, auto_zoom, scale_size, font_px, panel_width,
                     fit_width)


def test_zoom_presets():
    assert ZOOM_STEPS == (1.0, 1.25, 1.5, 2.0)


def test_auto_zoom_picks_the_largest_preset_that_fits():
    assert auto_zoom((1440, 900)) == 1.0     # 13" MacBook (points)
    assert auto_zoom((1512, 982)) == 1.0
    assert auto_zoom((1920, 1080)) == 1.0    # full HD: 125% would not fit vertically
    assert auto_zoom((1920, 1200)) == 1.25
    assert auto_zoom((2560, 1440)) == 1.5
    assert auto_zoom((2880, 1800)) == 2.0    # HiDPI laptop drawn in pixels (Linux)
    assert auto_zoom((3840, 2160)) == 2.0    # 4K
    assert auto_zoom((1280, 800)) == 1.0     # smaller than the design size
    assert auto_zoom(None) == 1.0


def test_scale_size_keeps_fill_and_auto():
    assert scale_size(636, 1.5) == 954
    assert scale_size(-670, 1.5) == -1005
    assert scale_size(45, 0.75) == 34
    assert scale_size(186.0, 1.25) == 232.5
    assert scale_size(-1, 2.0) == -1
    assert scale_size(0, 2.0) == 0


def test_panel_width_is_capped_when_zoomed():
    assert panel_width(660, 1.0, 1000) == 660   # 100% never changes
    assert panel_width(660, 1.5, 3000) == 990   # enough room: follows the zoom
    assert panel_width(660, 2.0, 1440) == 720   # capped at half the window


def test_fit_width_keeps_aspect_ratio():
    assert fit_width(636, 454, 700) == (636, 454)
    assert fit_width(1272, 908, 636) == (636, 454)


def test_font_px():
    assert font_px(13, 1.0) == 13
    assert font_px(13, 1.5) == 20
    assert font_px(20, 2.0) == 40
