"""Interface zoom: presets, the automatic choice for a screen, and size scaling (no GUI imports)."""

# Zoom presets; the layout is checked at each of them.
ZOOM_STEPS = (1.0, 1.25, 1.5, 2.0)

# Screen area the 100% layout is designed for.
DESIGN_SIZE = (1440, 900)


def auto_zoom(screen, design=DESIGN_SIZE) -> float:
    """The largest preset at which the layout still fits the screen; 1.0 if the screen is unknown."""
    if not screen:
        return 1.0
    fits = [z for z in ZOOM_STEPS if design[0] * z <= screen[0] and design[1] * z <= screen[1]]
    return max(fits, default=1.0)


def scale_size(value, zoom: float):
    """An explicit widget size at the given zoom. -1 (fill) and 0 (automatic) keep their meaning."""
    if value in (0, -1):
        return value
    if isinstance(value, float):
        return value * zoom
    return int(round(value * zoom))


def panel_width(base: int, zoom: float, viewport_w: int, max_share: float = 0.5) -> int:
    """Width of a side panel that is base px wide at 100%.

    It grows with the zoom but takes at most max_share of the window, so the
    node canvas next to it keeps its room. At 100% it is always base.
    """
    return min(scale_size(base, zoom), max(base, int(viewport_w * max_share)))


def fit_width(width: int, height: int, max_width: int):
    """(width, height) shrunk to at most max_width wide, keeping the aspect ratio."""
    if width <= max_width:
        return width, height
    return max_width, int(round(height * max_width / width))


def font_px(size: int, zoom: float) -> int:
    """Pixel size of a font of the given 100% size at this zoom."""
    return max(6, int(round(size * zoom)))
