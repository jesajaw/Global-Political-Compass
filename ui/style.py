"""
Central theme for the compass app -- same palette/scheme pattern as mtools' style.py
(same scheme names, same COLOR_SCHEME switch). Every window calls apply_style() once on
root/Toplevel and shares the same style names (Cell.TFrame, CellTitle.TLabel, Status.TLabel, ...).

Also holds the Windows-only fixes tkinter doesn't do by itself: DPI awareness (crisp text on
HiDPI screens), the dark title bar, and the taskbar/window icon.
"""

import sys
import ctypes
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk


def _is_win() -> bool:
    return sys.platform == "win32"


# -- DPI ---------------------------------------------------------------------------
# Must happen before the first Tk() exists, so it runs right here on import.
def enable_dpi_awareness() -> None:
    if not _is_win():
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # fallback for older Windows
        except Exception:
            pass


def _detect_scale() -> float:
    # 1.0 = 100 %, 1.5 = 150 % ... Tk scales *fonts* (points) by itself; this is for pixel sizes.
    if not _is_win():
        return 1.0
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


enable_dpi_awareness()
SCALE = _detect_scale()


def px(value: float) -> int:
    """A pixel size scaled to the display."""
    return round(value * SCALE)


# -- schemes -----------------------------------------------------------------------
_SCHEMES = {
    "dark_purple": dict(BG="#1e1e24", BG_LIGHT="#2a2a33", FG="#e0dff0", ACCENT="#9b59d9", ACCENT_DARK="#6c3fa0", STATUS_TEXT="#c9a6f5",),
    "dark_blue": dict(BG="#1e1e24", BG_LIGHT="#2a2a33", FG="#e0dff0", ACCENT="#4a90d9", ACCENT_DARK="#2f5f9e", STATUS_TEXT="#a6c9f5",),
    "black_white": dict(BG="#000000", BG_LIGHT="#1a1a1a", FG="#ffffff", ACCENT="#ffffff", ACCENT_DARK="#808080", STATUS_TEXT="#d9d9d9",),
}

_FONT_SCHEMES = {
    "segoe": dict(UI="Segoe UI", MONO="Consolas", SIZE_NORMAL=9, SIZE_HEADER=10, SIZE_TITLE=12),
    "system": dict(UI="TkDefaultFont", MONO="TkFixedFont", SIZE_NORMAL=9, SIZE_HEADER=10, SIZE_TITLE=12),
}

# switch palette / font preset here
COLOR_SCHEME = "dark_purple"
FONT_SCHEME = "segoe"

_active = _SCHEMES[COLOR_SCHEME]
COLOR_BG = _active["BG"]
COLOR_BG_LIGHT = _active["BG_LIGHT"]
COLOR_FG = _active["FG"]
COLOR = _active["ACCENT"]
COLOR_DARK = _active["ACCENT_DARK"]
COLOR_STATUS_TEXT = _active["STATUS_TEXT"]


def _mix(a: str, b: str, t: float) -> str:
    # blend colour a over b with strength t (tk has no alpha channel, so "transparent" tones are mixed by hand)
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * t + y * (1 - t)):02x}" for x, y in zip(ca, cb))


# tones the compass canvas needs, all derived from the base colours above
COLOR_GRID = _mix(COLOR_DARK, COLOR_BG_LIGHT, 0.35)
COLOR_AXIS = _mix(COLOR, COLOR_BG_LIGHT, 0.8)
COLOR_QUADRANT_LABEL = _mix(COLOR_STATUS_TEXT, COLOR_BG_LIGHT, 0.4)
COLOR_POINT = COLOR_STATUS_TEXT
COLOR_POINT_DIM = _mix(COLOR_DARK, COLOR_BG_LIGHT, 0.5)
COLOR_POINT_HOVER = COLOR
COLOR_POINT_HOVER_RING = COLOR_FG
COLOR_TOOLTIP_BG = COLOR_BG
COLOR_TOOLTIP_BORDER = COLOR_DARK
COLOR_HINT = _mix(COLOR_STATUS_TEXT, COLOR_BG_LIGHT, 0.55)

_active_font = _FONT_SCHEMES[FONT_SCHEME]
FONT_UI = _active_font["UI"]
FONT_MONO = _active_font["MONO"]
FONT_SIZE_NORMAL = _active_font["SIZE_NORMAL"]
FONT_SIZE_HEADER = _active_font["SIZE_HEADER"]
FONT_SIZE_TITLE = _active_font["SIZE_TITLE"]

# Ready-to-use (family, size[, weight]) tuples for style.configure() calls and any plain tk/ttk widget's font= option.
FONT_NORMAL = (FONT_UI, FONT_SIZE_NORMAL)
FONT_BOLD = (FONT_UI, FONT_SIZE_NORMAL, "bold")
FONT_HEADER = (FONT_UI, FONT_SIZE_HEADER, "bold")
FONT_TITLE = (FONT_UI, FONT_SIZE_TITLE, "bold")
FONT_MONO_NORMAL = (FONT_MONO, FONT_SIZE_NORMAL)
FONT_COUNTRY_LABEL = (FONT_UI, FONT_SIZE_NORMAL + 1)
FONT_TICK = (FONT_UI, FONT_SIZE_NORMAL - 1)
FONT_QUADRANT = (FONT_UI, FONT_SIZE_NORMAL + 1, "bold")


@dataclass(frozen=True)
class Layout:
    # Every number that goes into sizing/positioning the compass canvas and the control row, defined exactly once
    plot_padding: int = px(45)          # margin between canvas edge and the plot area
    point_radius: int = px(5)
    point_radius_hover: int = px(7)
    dim_radius: int = px(3)
    hover_hit_distance: int = px(14)
    tooltip_width: int = px(300)
    tooltip_padding: int = px(10)
    search_width_chars: int = 26
    combo_width_chars: int = 8
    control_height: int = px(40)
    data_button_width: int = px(90)
    data_window_size: str = f"{px(980)}x{px(680)}"


CELL_WIDTH = px(260)
CELL_HEIGHT = px(110)
LAYOUT = Layout()

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"


def apply_style(root) -> None:
    # Applies the theme to root (Tk or Toplevel): background + ttk styles

    root.configure(bg=COLOR_BG)
    apply_dark_titlebar(root)

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=COLOR_BG, foreground=COLOR_FG, font=FONT_NORMAL)
    style.configure("TFrame", background=COLOR_BG)
    style.configure("TLabelframe", background=COLOR_BG, foreground=COLOR_FG, bordercolor=COLOR_DARK)
    style.configure("TLabelframe.Label", background=COLOR_BG, foreground=COLOR)
    style.configure("TLabel", background=COLOR_BG, foreground=COLOR_FG)

    style.configure("TButton", background=COLOR_BG_LIGHT, foreground=COLOR_FG, bordercolor=COLOR_DARK, focusthickness=1, padding=6)
    style.map("TButton", background=[("active", COLOR_DARK), ("pressed", COLOR)], foreground=[("active", COLOR_FG)])

    style.configure("TCombobox", fieldbackground=COLOR_BG_LIGHT, background=COLOR_BG_LIGHT, foreground=COLOR_FG, arrowcolor=COLOR)
    style.map("TCombobox", fieldbackground=[("readonly", COLOR_BG_LIGHT)], foreground=[("readonly", COLOR_FG)])
    style.configure("Horizontal.TScale", background=COLOR_BG, troughcolor=COLOR_BG_LIGHT)
    style.configure("TEntry", fieldbackground=COLOR_BG_LIGHT, foreground=COLOR_FG, insertcolor=COLOR_FG)
    style.configure("Hint.TEntry", fieldbackground=COLOR_BG_LIGHT, foreground=COLOR_HINT, insertcolor=COLOR_FG)
    style.configure("TSpinbox", fieldbackground=COLOR_BG_LIGHT, background=COLOR_BG_LIGHT, foreground=COLOR_FG, arrowcolor=COLOR, insertcolor=COLOR_FG)

    style.configure("Accent.TButton", background=COLOR_DARK, foreground=COLOR_FG)
    style.map("Accent.TButton", background=[("active", COLOR)])

    style.configure("Cell.TFrame", background=COLOR_BG_LIGHT, bordercolor=COLOR_DARK)
    style.configure("Status.TLabel", background=COLOR_BG_LIGHT, foreground=COLOR_STATUS_TEXT, font=FONT_MONO_NORMAL)
    style.configure("CellTitle.TLabel", background=COLOR_BG_LIGHT, foreground=COLOR_FG, font=FONT_BOLD)

    # hover state for cells
    style.configure("CellHover.TFrame", background=COLOR_DARK, bordercolor=COLOR)
    style.configure("StatusHover.TLabel", background=COLOR_DARK, foreground=COLOR_STATUS_TEXT, font=FONT_MONO_NORMAL)
    style.configure("CellTitleHover.TLabel", background=COLOR_DARK, foreground=COLOR_FG, font=FONT_BOLD)

    style.configure("CategoryHeader.TLabel", background=COLOR_BG, foreground=COLOR, font=FONT_HEADER)
    style.configure("Title.TLabel", background=COLOR_BG, foreground=COLOR_FG, font=FONT_TITLE)
    style.configure("Note.TLabel", background=COLOR_BG, foreground=COLOR_STATUS_TEXT)

    # tree (data window)
    style.configure("Treeview", background=COLOR_BG_LIGHT, fieldbackground=COLOR_BG_LIGHT, foreground=COLOR_FG, bordercolor=COLOR_DARK, rowheight=px(24))
    style.map("Treeview", background=[("selected", COLOR_DARK)], foreground=[("selected", COLOR_FG)])
    style.configure("Treeview.Heading", background=COLOR_BG, foreground=COLOR, relief="flat", font=FONT_BOLD)
    style.map("Treeview.Heading", background=[("active", COLOR_BG_LIGHT)])
    style.configure("Vertical.TScrollbar", background=COLOR_DARK, troughcolor=COLOR_BG, bordercolor=COLOR_BG, arrowcolor=COLOR_FG)

    # plain tk widgets that ttk styles don't reach: the combobox drop-down and listboxes
    root.option_add("*TCombobox*Listbox.background", COLOR_BG_LIGHT)
    root.option_add("*TCombobox*Listbox.foreground", COLOR_FG)
    root.option_add("*TCombobox*Listbox.selectBackground", COLOR_DARK)
    root.option_add("*TCombobox*Listbox.selectForeground", COLOR_FG)


def style_listbox(widget) -> None:
    widget.configure(bg=COLOR_BG_LIGHT, fg=COLOR_FG, selectbackground=COLOR_DARK, selectforeground=COLOR_FG,
                     highlightthickness=1, highlightbackground=COLOR_DARK, highlightcolor=COLOR,
                     relief="flat", borderwidth=0, activestyle="none", font=FONT_NORMAL)


def style_text(widget) -> None:
    widget.configure(bg=COLOR_BG_LIGHT, fg=COLOR_FG, insertbackground=COLOR_FG, selectbackground=COLOR_DARK,
                     highlightthickness=1, highlightbackground=COLOR_DARK, highlightcolor=COLOR,
                     relief="flat", borderwidth=4, font=FONT_NORMAL, wrap="word")


# -- Windows-only: dark title bar, taskbar identity and icon ---------------------------
def apply_dark_titlebar(window) -> None:
    if not _is_win():
        return
    window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE: 20 (Win10 2004+), 19 (older)
        value = ctypes.c_int(1)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
        if result == 0:
            break


def force_dark_titlebar(window) -> None:
    if not _is_win():
        return
    window.update()
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        rendering_policy = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(rendering_policy), ctypes.sizeof(rendering_policy))
    except Exception:
        pass


def set_app_id(app_id: str = "GlobalPoliticalCompass.App.1") -> None:
    """
    Call once at the very start, before Tk() exists. Without an own AppUserModelID Windows groups
    the window under python.exe and shows *its* icon in the taskbar instead of ours.
    """
    if not _is_win():
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def set_window_icon(root) -> None:
    """Window + taskbar icon for `root` and every Toplevel opened later (default=...)."""
    if not ICON_PATH.exists():
        return
    try:
        root.iconbitmap(default=str(ICON_PATH))   # .ico is only understood by Tk on Windows
    except Exception:
        pass
