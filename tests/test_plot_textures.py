"""Plot textures are created on demand, so more than 8 plots can be shown."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

dpg = pytest.importorskip("dearpygui.dearpygui")
components = pytest.importorskip("ui.components")


@pytest.fixture
def registry():
    dpg.create_context()
    dpg.add_texture_registry(tag="texture_registry")
    yield
    dpg.destroy_context()


def test_textures_are_created_on_first_use(registry):
    assert not dpg.does_item_exist("plot_texture_buffer_19")
    tag = components.ensure_plot_texture(19)
    assert tag == "plot_texture_buffer_19"
    assert dpg.does_item_exist(tag)
    assert components.ensure_plot_texture(19) == tag     # idempotent


def test_a_twentieth_plot_loads(registry, tmp_path):
    from PIL import Image
    png = tmp_path / "hist_19.png"
    Image.new("RGBA", (636, 454), (255, 0, 0, 255)).save(png)
    assert components._load_png_to_texture(str(png), components.ensure_plot_texture(19))
    w, h = components.PLOT_TEXTURE_SIZE
    pixels = np.asarray(dpg.get_value("plot_texture_buffer_19"), dtype=float)
    assert pixels.size == w * h * 4
    assert pixels[0] == pytest.approx(1.0) and pixels[1] == pytest.approx(0.0)


def test_the_cap_is_above_eight():
    assert components.MAX_HIST_TEXTURES > 8
