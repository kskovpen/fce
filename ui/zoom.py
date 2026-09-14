"""Interface zoom: zoom steps, size scaling and the saved zoom level (no GUI imports)."""
import json

# Fixed zoom presets; the layout is checked at each of them.
ZOOM_STEPS = (1.0, 1.25, 1.5, 2.0)


def step_zoom(zoom: float, direction: int) -> float:
    """The zoom step above (direction > 0) or below (direction < 0) zoom, clamped to ZOOM_STEPS."""
    if direction > 0:
        return next((s for s in ZOOM_STEPS if s > zoom + 1e-6), ZOOM_STEPS[-1])
    return next((s for s in reversed(ZOOM_STEPS) if s < zoom - 1e-6), ZOOM_STEPS[0])


def nearest_step(zoom) -> float:
    """The zoom step closest to zoom; 1.0 for anything that is not a number."""
    try:
        z = float(zoom)
    except (TypeError, ValueError):
        return 1.0
    return min(ZOOM_STEPS, key=lambda s: abs(s - z))


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


def load_zoom(path: str) -> float:
    """The zoom saved in the settings file at path, or 1.0."""
    try:
        with open(path) as f:
            return nearest_step(json.load(f).get("zoom", 1.0))
    except (OSError, ValueError, AttributeError):
        return 1.0


def save_zoom(path: str, zoom: float) -> None:
    """Store zoom in the settings file at path, keeping any other settings in it."""
    data = {}
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        pass
    if not isinstance(data, dict):
        data = {}
    data["zoom"] = zoom
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except OSError:
        pass
