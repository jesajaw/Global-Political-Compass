"""
Central theme for the compass UI -- mirrors the palette/scheme pattern from
your mtools style.py (same scheme names, same COLOR_SCHEME switch), just
converted from hex strings to the RGBA tuples Dear PyGui expects instead of
ttk style.configure() calls.

Call apply_theme() once right after dpg.create_context(), and load_font()
once before dpg.setup_dearpygui().
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import dearpygui.dearpygui as dpg


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


# same three schemes as mtools/style.py
_SCHEMES = {
    "dark_purple": dict(BG="#1e1e24", BG_LIGHT="#2a2a33", FG="#e0dff0", ACCENT="#9b59d9", ACCENT_DARK="#6c3fa0", STATUS_TEXT="#c9a6f5"),
    "dark_blue": dict(BG="#1e1e24", BG_LIGHT="#2a2a33", FG="#e0dff0", ACCENT="#4a90d9", ACCENT_DARK="#2f5f9e", STATUS_TEXT="#a6c9f5"),
    "black_white": dict(BG="#000000", BG_LIGHT="#1a1a1a", FG="#ffffff", ACCENT="#ffffff", ACCENT_DARK="#808080", STATUS_TEXT="#d9d9d9"),
}

# Segoe UI on Windows if it's there, DPG's built-in font everywhere else --
# no "system" fallback scheme needed like in style.py since DPG always has
# a usable default font baked in.
_FONT_FILE_CANDIDATES = ("C:/Windows/Fonts/segoeui.ttf",)
_FONT_SIZE_NORMAL = 16
_FONT_SIZE_HEADER = 18

# switch palette here -- same switch as mtools/style.py
COLOR_SCHEME = "dark_purple"

_active = _SCHEMES[COLOR_SCHEME]
COLOR_BG = _hex_to_rgba(_active["BG"])
COLOR_BG_LIGHT = _hex_to_rgba(_active["BG_LIGHT"])
COLOR_FG = _hex_to_rgba(_active["FG"])
COLOR_ACCENT = _hex_to_rgba(_active["ACCENT"])
COLOR_ACCENT_DARK = _hex_to_rgba(_active["ACCENT_DARK"])
COLOR_STATUS_TEXT = _hex_to_rgba(_active["STATUS_TEXT"])

# a few tones the compass canvas needs that style.py has no direct
# equivalent for (grid lines, muted quadrant labels, dimmed points) --
# all still derived from the same three base colors above, nothing new.
COLOR_GRID = _hex_to_rgba(_active["ACCENT_DARK"], 90)
COLOR_QUADRANT_LABEL = _hex_to_rgba(_active["STATUS_TEXT"], 110)
COLOR_AXIS = _hex_to_rgba(_active["ACCENT"], 210)
COLOR_POINT_DIM = _hex_to_rgba(_active["BG_LIGHT"], 255)
COLOR_POINT = _hex_to_rgba(_active["STATUS_TEXT"], 230)
COLOR_POINT_HOVER_RING = _hex_to_rgba(_active["FG"], 255)
COLOR_POINT_HOVER = _hex_to_rgba(_active["ACCENT"], 255)
COLOR_TOOLTIP_BG = _hex_to_rgba(_active["BG"], 245)
COLOR_TOOLTIP_BORDER = _hex_to_rgba(_active["ACCENT_DARK"], 255)


@dataclass(frozen=True)
class Layout:
    padding: int = 45
    header_height: int = 46
    canvas_min: int = 400
    point_radius: float = 4.0
    point_radius_hover: float = 5.0
    hover_hit_distance: float = 14.0
    tooltip_w: int = 270
    tooltip_h: int = 105


LAYOUT = Layout()


def apply_theme() -> None:
    """Push the palette onto every DPG widget. Call once, right after dpg.create_context()."""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, COLOR_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, COLOR_BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, COLOR_BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, COLOR_ACCENT_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, COLOR_ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_Border, COLOR_ACCENT_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_Text, COLOR_FG)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, COLOR_STATUS_TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_Header, COLOR_ACCENT_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, COLOR_ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, COLOR_ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_Button, COLOR_BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, COLOR_ACCENT_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, COLOR_ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, COLOR_BG)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, COLOR_BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, COLOR_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, COLOR_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, COLOR_ACCENT_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, COLOR_ACCENT)

            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 12)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 8)

    dpg.bind_theme(global_theme)


def load_font() -> None:
    """
    Try to load the same UI font style.py uses (Segoe UI). Falls back to
    DPG's built-in font wherever that file doesn't exist (i.e. anywhere
    that isn't Windows) -- same intent as style.py's segoe/system switch,
    just resolved automatically instead of a second named scheme.
    """
    for path in _FONT_FILE_CANDIDATES:
        try:
            with dpg.font_registry():
                with dpg.font(path, _FONT_SIZE_NORMAL) as font:
                    dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
            dpg.bind_font(font)
            return
        except Exception:
            continue
    # no matching font file found -- keep DPG's default, nothing to do


def enable_dpi_awareness() -> None:
    # Same Windows-only DPI fix as mtools/style.py, no-op everywhere else.
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Process_Per_Monitor_DPI_Aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def enable_dark_titlebar(window_title: str) -> None:
    """
    Same DWM dark-titlebar trick as style.py's apply_dark_titlebar -- DPG
    doesn't expose an hwnd directly, so this looks the OS window up by its
    title instead (call it once, after dpg.show_viewport()).
    """
    if sys.platform != "win32":
        return
    import ctypes
    try:
        hwnd = ctypes.windll.user32.FindWindowW(None, window_title)
        if not hwnd:
            return
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass
