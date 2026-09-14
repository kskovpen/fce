"""Main display size, used to open the window at a size and zoom that fit the screen."""
import re
import subprocess
import sys


def parse_xrandr(text: str):
    """(width, height) of the primary connected output in `xrandr --query` output,
    else of the first connected output with a mode; None if there is none."""
    first = None
    for line in text.splitlines():
        m = re.match(r"^\S+ connected( primary)? (\d+)x(\d+)\+", line)
        if m:
            size = (int(m.group(2)), int(m.group(3)))
            if m.group(1):
                return size
            first = first or size
    return first


def _macos_size():
    import ctypes
    import ctypes.util

    class _Rect(ctypes.Structure):
        _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double),
                    ("w", ctypes.c_double), ("h", ctypes.c_double)]

    cg = ctypes.CDLL(ctypes.util.find_library("CoreGraphics"))
    cg.CGMainDisplayID.restype = ctypes.c_uint32
    cg.CGDisplayBounds.argtypes = [ctypes.c_uint32]
    cg.CGDisplayBounds.restype = _Rect
    rect = cg.CGDisplayBounds(cg.CGMainDisplayID())
    return int(rect.w), int(rect.h)


def _windows_size():
    import ctypes
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)  # SM_CXSCREEN, SM_CYSCREEN


def _load(name: str, soname: str):
    import ctypes
    import ctypes.util
    return ctypes.CDLL(ctypes.util.find_library(name) or soname)


def _xrandr_primary(x11, display):
    """Size of the primary (else first) monitor reported by the RandR extension."""
    import ctypes

    class _Monitor(ctypes.Structure):  # XRRMonitorInfo
        _fields_ = [("name", ctypes.c_ulong), ("primary", ctypes.c_int),
                    ("automatic", ctypes.c_int), ("noutput", ctypes.c_int),
                    ("x", ctypes.c_int), ("y", ctypes.c_int),
                    ("width", ctypes.c_int), ("height", ctypes.c_int),
                    ("mwidth", ctypes.c_int), ("mheight", ctypes.c_int),
                    ("outputs", ctypes.c_void_p)]

    xrr = _load("Xrandr", "libXrandr.so.2")
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    xrr.XRRGetMonitors.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int,
                                   ctypes.POINTER(ctypes.c_int)]
    xrr.XRRGetMonitors.restype = ctypes.POINTER(_Monitor)
    xrr.XRRFreeMonitors.argtypes = [ctypes.POINTER(_Monitor)]
    count = ctypes.c_int(0)
    monitors = xrr.XRRGetMonitors(display, x11.XDefaultRootWindow(display), 1,
                                  ctypes.byref(count))
    if not monitors:
        return None
    try:
        found = [monitors[i] for i in range(count.value)]
        chosen = next((m for m in found if m.primary), found[0] if found else None)
        return (chosen.width, chosen.height) if chosen else None
    finally:
        xrr.XRRFreeMonitors(monitors)


def _x11_size():
    """Screen size from the X server (Xorg, or XWayland on Wayland desktops) via
    the X libraries, which the app's window layer needs on any distribution."""
    import ctypes
    x11 = _load("X11", "libX11.so.6")
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = x11.XOpenDisplay(None)
    if not display:
        return None
    try:
        try:
            size = _xrandr_primary(x11, display)
            if size:
                return size
        except Exception:
            pass
        # Without RandR: the whole X screen (all monitors together)
        x11.XDefaultScreen.argtypes = [ctypes.c_void_p]
        x11.XDisplayWidth.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XDisplayHeight.argtypes = [ctypes.c_void_p, ctypes.c_int]
        screen = x11.XDefaultScreen(display)
        return x11.XDisplayWidth(display, screen), x11.XDisplayHeight(display, screen)
    finally:
        x11.XCloseDisplay(display)


def _linux_size():
    try:
        size = _x11_size()
        if size:
            return size
    except Exception:
        pass
    out = subprocess.run(["xrandr", "--query"], capture_output=True, text=True,
                         timeout=3).stdout
    return parse_xrandr(out)


def screen_size():
    """(width, height) of the main display in the units the window uses
    (points on macOS, pixels on Linux/X11); None if it cannot be determined."""
    getter = {"darwin": _macos_size, "win32": _windows_size}.get(sys.platform)
    if getter is None and sys.platform.startswith("linux"):
        getter = _linux_size
    if getter is None:
        return None
    try:
        size = getter()
    except Exception:
        return None
    if size and size[0] > 0 and size[1] > 0:
        return size
    return None


def fit_window(width: int, height: int, screen, reserved_h: int = 100):
    """(width, height) reduced to fit the screen, keeping reserved_h px free
    vertically for the menu bar/taskbar and the window title bar."""
    if not screen:
        return width, height
    return min(width, screen[0]), min(height, screen[1] - reserved_h)
