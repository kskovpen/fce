import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.zoom import (ZOOM_STEPS, step_zoom, nearest_step, scale_size, font_px,
                     panel_width, fit_width, load_zoom, save_zoom)


def test_zoom_presets():
    assert ZOOM_STEPS == (1.0, 1.25, 1.5, 2.0)


def test_step_zoom_moves_one_preset_and_clamps():
    assert step_zoom(1.0, +1) == 1.25
    assert step_zoom(1.5, +1) == 2.0
    assert step_zoom(1.25, -1) == 1.0
    assert step_zoom(2.0, +1) == 2.0
    assert step_zoom(1.0, -1) == 1.0
    # A zoom between presets moves to the neighbouring preset
    assert step_zoom(1.3, +1) == 1.5
    assert step_zoom(1.3, -1) == 1.25


def test_nearest_step():
    assert nearest_step(1.3) == 1.25
    assert nearest_step(1.75) in (1.5, 2.0)
    assert nearest_step(0.75) == 1.0   # an old saved zoom-out level
    assert nearest_step(9) == 2.0
    assert nearest_step("bad") == 1.0
    assert nearest_step(None) == 1.0


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
    assert panel_width(660, 0.75, 1440) == 495


def test_fit_width_keeps_aspect_ratio():
    assert fit_width(636, 454, 700) == (636, 454)
    assert fit_width(1272, 908, 636) == (636, 454)


def test_font_px():
    assert font_px(13, 1.0) == 13
    assert font_px(13, 1.5) == 20
    assert font_px(13, 0.75) == 10
    assert font_px(20, 2.0) == 40


def test_zoom_setting_roundtrip(tmp_path):
    path = tmp_path / "ui_settings.json"
    assert load_zoom(str(path)) == 1.0
    save_zoom(str(path), 1.5)
    assert load_zoom(str(path)) == 1.5
    path.write_text("{not json")
    assert load_zoom(str(path)) == 1.0
    path.write_text('{"other": 1}')
    save_zoom(str(path), 1.25)
    assert json.loads(path.read_text()) == {"other": 1, "zoom": 1.25}
