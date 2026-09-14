"""Whole-interface zoom: Ctrl/Cmd + mouse wheel, Ctrl/Cmd + = / - / 0, View menu.

At 100% the interface is left exactly as built. At other zoom steps the UI font
is swapped for a copy rendered at that size, explicit widget sizes are scaled
from their 100% values, spacing is scaled through a global theme and nodes are
spread out on the canvas. Widgets created later (new nodes, plots, popups) are
picked up by a periodic pass.
"""
import os
import time

import dearpygui.dearpygui as dpg

import ui.state as _state
from ui.zoom import (ZOOM_STEPS, step_zoom, scale_size, panel_width, fit_width,
                     load_zoom, save_zoom)
from paths import get_fce_home

_SETTINGS_FILE = os.path.join(get_fce_home(), "ui_settings.json")

# ImGui key codes; DearPyGui has no constants for the Super (Cmd) keys or "=".
_KEY_LSUPER, _KEY_RSUPER, _KEY_EQUAL = 530, 534, 602
_MODIFIER_KEYS = (dpg.mvKey_LControl, dpg.mvKey_RControl, _KEY_LSUPER, _KEY_RSUPER)

# Explicit sizes that follow the zoom, per item type.
_SIZE_KEYS = {
    "mvButton": ("width", "height"),
    "mvImage": ("width", "height"),
    "mvChildWindow": ("width", "height"),
    "mvWindowAppItem": ("width", "height"),
    "mvFileDialog": ("width", "height"),
    "mvGroup": ("width",),
    "mvSpacer": ("width", "height"),
    "mvInputText": ("width", "height"),
    "mvInputInt": ("width",),
    "mvInputFloat": ("width",),
    "mvInputDouble": ("width",),
    "mvCombo": ("width",),
    "mvProgressBar": ("width", "height"),
    "mvSliderInt": ("width",),
    "mvSliderFloat": ("width",),
    "mvListbox": ("width",),
    "mvText": ("wrap",),
    "mvTableColumn": ("init_width_or_weight",),
}
_SKIP_TAGS = ("primary_studio_window",)

# The right-hand panel (660 px at 100%) and the node canvas share the window:
# when zoomed the panel takes at most half of it and its plots are fitted inside.
_PANEL_W, _PANEL_GAP, _PLOT_MARGIN = 660, 10, 24
_PLOT_TAGS = ("canvas_view_frame_", "cutflow_view_frame")
_LAYOUT_TAGS = ("right_panel", "node_editor_pane") + _PLOT_TAGS
_WINDOW_MARGIN = 40  # px kept free around a zoomed popup window (clears the menu bar)
# Rows of two side-by-side halves, stacked on two lines while zoomed in.
_STACK_WHEN_ZOOMED = ("node_state_legend",)

# Style values at 100% (Dear ImGui / imnodes defaults), scaled while zoomed.
_STYLE_VARS = (
    (dpg.mvStyleVar_WindowPadding, 8, 8),
    (dpg.mvStyleVar_FramePadding, 4, 3),
    (dpg.mvStyleVar_ItemSpacing, 8, 4),
    (dpg.mvStyleVar_ItemInnerSpacing, 4, 4),
    (dpg.mvStyleVar_CellPadding, 4, 2),
    (dpg.mvStyleVar_IndentSpacing, 21),
    (dpg.mvStyleVar_ScrollbarSize, 14),
)
_NODE_STYLE_VARS = (
    (dpg.mvNodeStyleVar_GridSpacing, 24),
    (dpg.mvNodeStyleVar_NodePadding, 8, 8),
    (dpg.mvNodeStyleVar_NodeCornerRounding, 4),
    (dpg.mvNodeStyleVar_PinCircleRadius, 4),
    (dpg.mvNodeStyleVar_PinHoverRadius, 10),
    (dpg.mvNodeStyleVar_LinkThickness, 3),
    (dpg.mvNodeStyleVar_LinkHoverDistance, 10),
)
_THEME_TAG = "zoom_spacing_theme"

_TICK_FRAMES = 15             # frames between passes over newly created widgets
_WHEEL_STEP_INTERVAL = 0.08   # seconds between zoom steps while the wheel keeps turning

_ZOOM = [1.0]
_FONTS: dict = {}      # zoom -> {"base": font (0 = built-in), "large": font, "ext": font}
_FONT_ROLE: dict = {}  # font id -> "large" / "ext"
_BASE: dict = {}       # item id -> {config key: size at 100%}; {} = nothing to scale
_WINDOWS: set = set()  # popup windows, kept inside the viewport while zoomed
_WHEEL = [0.0, 0.0]    # accumulated wheel delta, time of the last wheel zoom step


def zoom_modifier_down() -> bool:
    """True while Ctrl or Cmd is held."""
    return any(dpg.is_key_down(k) for k in _MODIFIER_KEYS)


def scaled(value):
    """A size given at 100% at the current zoom."""
    return scale_size(value, _ZOOM[0])


def _fit_layout(alias: str, sizes: dict, zoom: float) -> dict:
    """Adjust scaled sizes of the panel/canvas split and of the plots in the panel."""
    if not alias:
        return sizes
    panel = panel_width(_PANEL_W, zoom, dpg.get_viewport_client_width())
    if alias == "right_panel":
        sizes["width"] = panel
    elif alias == "node_editor_pane":
        sizes["width"] = -(panel + scale_size(_PANEL_GAP, zoom))
    elif alias.startswith(_PLOT_TAGS) and "width" in sizes and "height" in sizes:
        sizes["width"], sizes["height"] = fit_width(
            sizes["width"], sizes["height"], panel - scale_size(_PLOT_MARGIN, zoom))
    return sizes


def _fit_viewport(sizes: dict) -> dict:
    """Keep a zoomed popup window inside the viewport."""
    limits = {"width": dpg.get_viewport_client_width(),
              "height": dpg.get_viewport_client_height()}
    for key, limit in limits.items():
        if key in sizes and limit > 2 * _WINDOW_MARGIN:
            sizes[key] = min(sizes[key], limit - 2 * _WINDOW_MARGIN)
    return sizes


def _scale_item(item, zoom: float) -> None:
    """Record the item's 100% sizes the first time it is seen, and apply zoom to them."""
    base = _BASE.get(item)
    if base is None:
        kind = dpg.get_item_type(item).rsplit("::", 1)[-1]
        keys = _SIZE_KEYS.get(kind, ())
        if dpg.get_item_alias(item) in _SKIP_TAGS:
            keys = ()
        cfg = dpg.get_item_configuration(item) if keys else {}
        if kind == "mvTableColumn" and not cfg.get("width_fixed"):
            keys = ()  # a stretch column's value is a weight, not pixels
        if kind == "mvWindowAppItem" and keys:
            _WINDOWS.add(item)
        base = {k: cfg[k] for k in keys if k in cfg and cfg[k] not in (0, -1)}
        _BASE[item] = base
    if base:
        sizes = _fit_layout(dpg.get_item_alias(item),
                            {k: scale_size(v, zoom) for k, v in base.items()}, zoom)
        if item in _WINDOWS and zoom != 1.0:
            sizes = _fit_viewport(sizes)
        dpg.configure_item(item, **sizes)


def _on_viewport_resize(sender=None, app_data=None, user_data=None):
    """Re-fit the panel/canvas split and the popup windows to the new window size."""
    for item, base in list(_BASE.items()):
        if base and dpg.does_item_exist(item) and (
                item in _WINDOWS or dpg.get_item_alias(item).startswith(_LAYOUT_TAGS)):
            _scale_item(item, _ZOOM[0])


def rescale_new_items() -> None:
    """Scale widgets created since the last pass."""
    zoom = _ZOOM[0]
    if zoom == 1.0:
        return
    for item in dpg.get_all_items():
        if item not in _BASE:
            try:
                _scale_item(item, zoom)
            except Exception:
                _BASE[item] = {}


def _scale_node_positions(ratio: float) -> None:
    if ratio == 1.0:
        return
    for nid in list(_state.REGISTRY.nodes):
        tag = f"node_{nid}"
        if dpg.does_item_exist(tag):
            x, y = dpg.get_item_pos(tag)
            dpg.set_item_pos(tag, [x * ratio, y * ratio])


def _bind_spacing_theme(zoom: float) -> None:
    dpg.bind_theme(0)
    if dpg.does_item_exist(_THEME_TAG):
        dpg.delete_item(_THEME_TAG)
    if zoom == 1.0:
        return
    with dpg.theme(tag=_THEME_TAG):
        with dpg.theme_component(dpg.mvAll):
            for var, *values in _STYLE_VARS:
                dpg.add_theme_style(var, *(v * zoom for v in values),
                                    category=dpg.mvThemeCat_Core)
            for var, *values in _NODE_STYLE_VARS:
                dpg.add_theme_style(var, *(v * zoom for v in values),
                                    category=dpg.mvThemeCat_Nodes)
    dpg.bind_theme(_THEME_TAG)


def set_zoom(zoom: float, save: bool = True) -> None:
    """Zoom the whole interface to one of the ZOOM_STEPS."""
    old = _ZOOM[0]
    if zoom == old:
        return
    fonts = _FONTS.get(zoom, {})
    dpg.bind_font(fonts.get("base") or 0)
    _state.LARGE_FONT = fonts.get("large") or _state.LARGE_FONT
    _state.EXTENDED_FONT = fonts.get("ext") or _state.EXTENDED_FONT
    _ZOOM[0] = zoom
    for item in dpg.get_all_items():
        try:
            _scale_item(item, zoom)
            role = _FONT_ROLE.get(dpg.get_item_info(item).get("font"))
            if role and fonts.get(role):
                dpg.bind_item_font(item, fonts[role])
        except Exception:
            _BASE.setdefault(item, {})
    for item in [i for i in _BASE if not dpg.does_item_exist(i)]:
        del _BASE[item]
        _WINDOWS.discard(item)
    for tag in _STACK_WHEN_ZOOMED:
        if dpg.does_item_exist(tag):
            dpg.configure_item(tag, horizontal=zoom <= 1.0)
    _scale_node_positions(zoom / old)
    _bind_spacing_theme(zoom)
    _sync_zoom_menu()
    if save:
        save_zoom(_SETTINGS_FILE, zoom)
    from ui.components import log_to_message_center
    log_to_message_center(f"Zoom: {round(zoom * 100)}%")


def zoom_menu_tag(zoom: float) -> str:
    """Tag of the View-menu item for a zoom preset."""
    return f"zoom_menu_{round(zoom * 100)}"


def _sync_zoom_menu() -> None:
    for step in ZOOM_STEPS:
        if dpg.does_item_exist(zoom_menu_tag(step)):
            dpg.set_value(zoom_menu_tag(step), step == _ZOOM[0])


def zoom_preset(sender=None, app_data=None, user_data=None):
    """View-menu callback; user_data is the preset."""
    set_zoom(user_data)
    _sync_zoom_menu()  # clicking the current preset must not untick it


def zoom_in(sender=None, app_data=None, user_data=None):
    set_zoom(step_zoom(_ZOOM[0], +1))


def zoom_out(sender=None, app_data=None, user_data=None):
    set_zoom(step_zoom(_ZOOM[0], -1))


def zoom_reset(sender=None, app_data=None, user_data=None):
    set_zoom(1.0)


def center_window(tag) -> None:
    """Centre a popup window in the viewport at its current (zoomed) size."""
    rescale_new_items()
    w = dpg.get_item_width(tag) or 0
    h = dpg.get_item_height(tag) or 0
    dpg.set_item_pos(tag, [max(0, (dpg.get_viewport_width() - w) // 2),
                           max(0, (dpg.get_viewport_height() - h) // 2)])


def _on_mouse_wheel(sender, app_data):
    if not zoom_modifier_down():
        return
    # Trackpads send many small deltas: step once per notch, not per event.
    _WHEEL[0] += float(app_data)
    now = time.monotonic()
    if abs(_WHEEL[0]) < 1.0 or now - _WHEEL[1] < _WHEEL_STEP_INTERVAL:
        return
    direction = 1 if _WHEEL[0] > 0 else -1
    _WHEEL[0], _WHEEL[1] = 0.0, now
    set_zoom(step_zoom(_ZOOM[0], direction))


def _on_zoom_key(sender, app_data, user_data):
    if zoom_modifier_down():
        user_data()


def _tick(sender=None, app_data=None, user_data=None):
    rescale_new_items()
    dpg.set_frame_callback(dpg.get_frame_count() + _TICK_FRAMES, _tick)


def setup_zoom(fonts: dict) -> None:
    """Register the per-step fonts and the mouse/keyboard zoom handlers.

    fonts: {zoom: {"base": font (0 = built-in), "large": font, "ext": font}}.
    """
    _FONTS.update(fonts)
    for per_step in fonts.values():
        for role in ("large", "ext"):
            if per_step.get(role):
                _FONT_ROLE[per_step[role]] = role
    with dpg.handler_registry():
        dpg.add_mouse_wheel_handler(callback=_on_mouse_wheel)
        for keys, action in (((_KEY_EQUAL, dpg.mvKey_Add), zoom_in),
                             ((dpg.mvKey_Minus, dpg.mvKey_Subtract), zoom_out),
                             ((dpg.mvKey_0, dpg.mvKey_NumPad0), zoom_reset)):
            for key in keys:
                dpg.add_key_press_handler(key=key, callback=_on_zoom_key, user_data=action)


def start_zoom() -> None:
    """Restore the saved zoom and start picking up new widgets (call on the first frame)."""
    dpg.set_viewport_resize_callback(_on_viewport_resize)
    zoom = load_zoom(_SETTINGS_FILE)
    if zoom != 1.0:
        set_zoom(zoom, save=False)
    _tick()
