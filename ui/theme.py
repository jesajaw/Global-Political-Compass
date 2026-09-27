"""
Central theme for the compass app -- mirrors the palette/scheme pattern
from your mtools style.py (same scheme names, same COLOR_SCHEME switch),
just converted from hex strings to the RGBA tuples Dear PyGui expects
instead of ttk style.configure() calls.

Every visual constant both windows use (colors, sizes, spacing) is defined
here and nowhere else -- compass_window/ and data_editor_window/ only ever
*read* theme.* / theme.LAYOUT.*, they never hardcode a color or a pixel
size of their own.

Call apply_theme() once right after dpg.create_context(), and load_font()
once before dpg.setup_dearpygui(). get_screen_size() is used by ui/app.py
to size the viewport at launch (80% of the screen).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import dearpygui.dearpygui as dpg

# repo_root/assets/icon.ico -- see get_icon_path() below
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"


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

# switch palette here -- same switch as mtools/style.py
COLOR_SCHEME = "dark_purple"

# how much bigger than the original draft everything (fonts, padding,
# controls) should be -- 1.0 would be the original, cramped sizing
UI_SCALE = 1.45

# Segoe UI on Windows if it's there, DPG's built-in font everywhere else --
# no "system" fallback scheme needed like in style.py since DPG always has
# a usable default font baked in.
_FONT_FILE_CANDIDATES = ("C:/Windows/Fonts/segoeui.ttf",)
_FONT_SIZE_NORMAL = round(16 * UI_SCALE)
# if no font file is found (i.e. not on Windows), DPG's default bitmap font
# is scaled up via set_global_font_scale instead, so the "bigger" request
# still holds cross-platform
_FALLBACK_FONT_SCALE = UI_SCALE

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
    padding: int = round(45 * UI_SCALE)
    # the slim row of controls (search / year / Data button) now lives
    # below the plot instead of above it -- same idea as the old
    # header_height, just reserved at the bottom of the window now
    control_bar_height: int = round(46 * UI_SCALE)
    canvas_min: int = round(400 * UI_SCALE)
    # the same WindowPadding pushed onto every dpg widget in apply_theme()
    # below -- exposed here too so window.py can size the canvas "cell"
    # (the child_window around the drawlist) without duplicating the number
    window_padding: int = round(12 * UI_SCALE)
    # no zoom -- the default view is the only view, so points/hover ring
    # need to read clearly on their own, not just when zoomed in
    point_radius: float = 6.0 * UI_SCALE
    point_radius_hover: float = 8.0 * UI_SCALE
    hover_hit_distance: float = 14.0 * UI_SCALE
    tooltip_w: int = round(280 * UI_SCALE)
    tooltip_h: int = round(115 * UI_SCALE)
    search_width: int = round(220 * UI_SCALE)
    combo_width: int = round(100 * UI_SCALE)
    # the corner "open data editor" button became a normal bottom-bar
    # button (no longer floating over the canvas corner), so it gets a
    # plain readable width/height like the other controls now
    data_button_w: int = round(70 * UI_SCALE)
    data_button_h: int = round(30 * UI_SCALE)

    # -- canvas text sizes ------------------------------------------------
    # dpg.draw_text() defaults to a tiny fixed size (~10px) that ignores
    # UI_SCALE and the bound font entirely -- every draw_text call in
    # compass_window/view.py must pass one of these explicitly, or it goes
    # right back to being unreadable regardless of window size.
    axis_label_size: int = round(15 * UI_SCALE)
    quadrant_label_size: int = round(13 * UI_SCALE)
    country_label_size: int = round(14 * UI_SCALE)
    tooltip_title_size: int = round(16 * UI_SCALE)
    tooltip_text_size: int = round(13 * UI_SCALE)
    # the numeric tick labels along both axes (-100..100) -- deliberately
    # a notch smaller than axis_label_size, they're a lot of small numbers
    # rather than a couple of words
    tick_label_size: int = round(11 * UI_SCALE)


LAYOUT = Layout()


def get_screen_size() -> tuple[int, int]:
    """
    Physical monitor resolution, used to size the viewport at 80% before it
    exists (DPG has no "current monitor size" query pre-viewport). Tries
    Windows first, then falls back to a throwaway Tk root (stdlib, works on
    Linux/macOS too), and finally a hardcoded guess if neither works.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            pass
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return w, h
    except Exception:
        return 1920, 1080


def get_icon_path() -> str | None:
    """
    Path to the taskbar/titlebar icon (assets/icon.ico), for
    dpg.create_viewport(small_icon=..., large_icon=...). Currently a plain
    black placeholder square -- see assets/icon.ico's own docstring-less
    nature; swap that file out for a real icon whenever one's ready, no
    code change needed. Returns None (DPG's own default) if it's missing.
    """
    return str(ICON_PATH) if ICON_PATH.exists() else None


def apply_theme() -> None:
    """Push the palette onto every DPG widget. Call once, right after dpg.create_context()."""
    pad = LAYOUT.window_padding
    spacing = round(8 * UI_SCALE)
    rounding = round(4 * UI_SCALE)

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

            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, rounding)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, round(6 * UI_SCALE))
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, pad, pad)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, round(4 * UI_SCALE), round(3 * UI_SCALE))
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, spacing, spacing)

    dpg.bind_theme(global_theme)


def load_font() -> None:
    """
    Try to load the same UI font style.py uses (Segoe UI), at the scaled-up
    size. Falls back to scaling DPG's built-in font wherever that file
    doesn't exist (i.e. anywhere that isn't Windows) -- same intent as
    style.py's segoe/system switch, just resolved automatically.
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
    # no matching font file found -- scale DPG's default font instead so the
    # "bigger, more readable" request still holds on non-Windows machines
    dpg.set_global_font_scale(_FALLBACK_FONT_SCALE)


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
