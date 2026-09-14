import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.screen import (screen_size, fit_window, parse_xrandr, parse_xft_dpi,
                       desktop_scale)

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


def test_parse_xft_dpi():
    assert parse_xft_dpi("Xft.antialias:\t1\nXft.dpi:\t192\nXft.hinting:\t1\n") == 192.0
    assert parse_xft_dpi("Xft.dpi: 120.5") == 120.5
    assert parse_xft_dpi("Xcursor.size:\t48\n") is None
    assert parse_xft_dpi("Xft.dpi:\tlarge\n") is None
    assert parse_xft_dpi("") is None


def test_desktop_scale_is_positive():
    scale = desktop_scale()
    assert scale > 0
    if sys.platform == "darwin":
        assert scale == 1.0   # macOS sizes are already in points


def test_desktop_scale_macos_is_always_1(monkeypatch):
    from ui import screen
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("GDK_SCALE", "2")
    monkeypatch.setattr(screen, "_x11_scale", lambda: 2.0)
    assert screen.desktop_scale() == 1.0


def test_desktop_scale_windows_uses_system_dpi(monkeypatch):
    import ctypes
    from ui import screen

    class _User32:
        dpi = 144

        def GetDpiForSystem(self):
            return self.dpi

    class _WinDLL:
        user32 = _User32()

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", _WinDLL(), raising=False)
    assert screen.desktop_scale() == 1.5
    _User32.dpi = 96   # Windows scales a DPI-unaware app itself
    assert screen.desktop_scale() == 1.0
    monkeypatch.delattr(ctypes, "windll")
    assert screen.desktop_scale() == 1.0   # no DPI API: no zoom


def test_desktop_scale_linux_order(monkeypatch):
    from ui import screen
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("GDK_SCALE", raising=False)
    monkeypatch.delenv("QT_SCALE_FACTOR", raising=False)
    monkeypatch.setattr(screen, "_x11_physical_scale", lambda: 2.0)
    monkeypatch.setattr(screen, "_x11_scale", lambda: 1.5)     # Xft.dpi 144 wins
    assert screen.desktop_scale() == 1.5
    monkeypatch.setattr(screen, "_x11_scale", lambda: None)    # no Xft.dpi
    monkeypatch.setenv("GDK_SCALE", "2")
    monkeypatch.setattr(screen, "_x11_physical_scale", lambda: 1.0)
    assert screen.desktop_scale() == 2.0                        # environment next
    monkeypatch.delenv("GDK_SCALE")
    monkeypatch.setattr(screen, "_x11_physical_scale", lambda: 2.0)
    assert screen.desktop_scale() == 2.0                        # then physical DPI

    def _fail():
        raise OSError("no X display")
    monkeypatch.setattr(screen, "_x11_scale", _fail)
    monkeypatch.setattr(screen, "_x11_physical_scale", _fail)
    assert screen.desktop_scale() == 1.0                        # nothing known


def test_screen_size_is_none_or_positive():
    size = screen_size()
    assert size is None or (size[0] > 0 and size[1] > 0)
