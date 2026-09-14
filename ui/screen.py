"""Main display size, used to open the window at a size that fits the screen."""
import sys


def screen_size():
    """(width, height) of the main display in points on macOS; None elsewhere or on failure.

    DearPyGui cannot maximize the window on macOS, so the app sizes it itself.
    """
    if sys.platform != "darwin":
        return None
    try:
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
        if rect.w > 0 and rect.h > 0:
            return int(rect.w), int(rect.h)
    except Exception:
        pass
    return None


def fit_window(width: int, height: int, screen, reserved_h: int = 100):
    """(width, height) reduced to fit the screen, keeping reserved_h px free
    vertically for the menu bar and the window title bar."""
    if not screen:
        return width, height
    return min(width, screen[0]), min(height, screen[1] - reserved_h)
