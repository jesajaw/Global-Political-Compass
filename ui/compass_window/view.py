"""
Rendering for the compass canvas: grid, axes, country points, hover tooltip.

The maths (val_to_px / compute_visible_points / find_hovered) are plain functions with no tkinter in
them. CompassCanvas draws them on a tk.Canvas in two layers so mouse movement stays cheap:

  - the base layer (grid, axes, points, hover ring) is redrawn only when something that changes the
    picture changed: window resized, year/search changed, data changed, or the hovered country changed
  - the tooltip layer (tag "tip") is redrawn on every mouse move while a country is hovered

The values it plots come from data.scoring.get_scores(year) -- the average of all entries of that year.
"""

from __future__ import annotations

import math
import tkinter as tk

from data import scoring, store
from .. import style
from ..style import LAYOUT


# -- pure maths (no tkinter) -----------------------------------------------------------

def val_to_px(left_right: float, lib_auth: float, w: int, h: int) -> tuple[float, float]:
    pad = LAYOUT.plot_padding
    x = pad + ((left_right + 100) / 200.0) * (w - 2 * pad)
    y = pad + ((100 - lib_auth) / 200.0) * (h - 2 * pad)
    return x, y


def compute_visible_points(scores: dict, countries: dict, search_query: str, w: int, h: int) -> list[dict]:
    """scores: {country_id: Score}; countries: {country_id: Country}."""
    points = []
    for country_id, score in scores.items():
        country = countries[country_id]
        px, py = val_to_px(score.left_right, score.lib_auth, w, h)
        matches = not search_query or search_query in country.name.lower()
        points.append({"country": country, "score": score, "px": px, "py": py, "match": matches})
    return points


def find_hovered(points: list[dict], mx: float, my: float) -> dict | None:
    hovered = None
    for p in points:
        if p["match"] and math.hypot(mx - p["px"], my - p["py"]) < LAYOUT.hover_hit_distance:
            hovered = p          # later points sit on top, so the last hit wins
    return hovered


def fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


# -- the canvas ------------------------------------------------------------------------------

class CompassCanvas(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, bg=style.COLOR_BG_LIGHT, highlightthickness=1,
                         highlightbackground=style.COLOR_DARK, bd=0)
        self.year = ""
        self.search_query = ""
        self._points: list[dict] = []
        self._hovered: dict | None = None

        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)

    # -- state from the window ---------------------------------------------------------

    def set_year(self, year: str) -> None:
        self.year = year
        self.redraw()

    def set_search(self, query: str) -> None:
        self.search_query = query.lower().strip()
        self.redraw()

    def refresh(self) -> None:
        """Data changed underneath (an entry was added/edited/deleted): re-read and redraw."""
        self.redraw()

    # -- drawing -------------------------------------------------------------------------

    def redraw(self) -> None:
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            return                                   # not laid out yet; <Configure> will call us again
        self.delete("all")

        scores = scoring.get_scores(self.year) if self.year else {}
        countries = {c.index: c for c in store.countries()}
        self._points = compute_visible_points(scores, countries, self.search_query, w, h)
        if self._hovered is not None:                 # keep the hover ring across a redraw if that country is still there
            hid = self._hovered["country"].index
            self._hovered = next((p for p in self._points if p["country"].index == hid and p["match"]), None)

        self._draw_quadrant_labels(w, h)
        self._draw_grid(w, h)
        self._draw_axes(w, h)
        self._draw_ticks(w, h)
        self._draw_points()
        if not self._points:
            self._draw_empty_note(w, h)

    def _draw_quadrant_labels(self, w: int, h: int) -> None:
        pad = LAYOUT.plot_padding
        off = style.px(10)
        kw = dict(fill=style.COLOR_QUADRANT_LABEL, font=style.FONT_QUADRANT)
        self.create_text(pad + off, pad + off, text="AUTHORITARIAN LEFT", anchor="nw", **kw)
        self.create_text(pad + off, h - pad - off, text="LIBERTARIAN LEFT", anchor="sw", **kw)
        self.create_text(w - pad - off, pad + off, text="AUTHORITARIAN RIGHT", anchor="ne", **kw)
        self.create_text(w - pad - off, h - pad - off, text="LIBERTARIAN RIGHT", anchor="se", **kw)

    def _draw_grid(self, w: int, h: int) -> None:
        pad = LAYOUT.plot_padding
        for i in range(-80, 90, 20):
            if i == 0:
                continue
            px, py = val_to_px(i, i, w, h)
            self.create_line(px, pad, px, h - pad, fill=style.COLOR_GRID)
            self.create_line(pad, py, w - pad, py, fill=style.COLOR_GRID)

    def _draw_axes(self, w: int, h: int) -> None:
        pad = LAYOUT.plot_padding
        cx, cy = w / 2.0, h / 2.0
        self.create_line(cx, pad, cx, h - pad, fill=style.COLOR_AXIS, width=2)
        self.create_line(pad, cy, w - pad, cy, fill=style.COLOR_AXIS, width=2)

    def _draw_ticks(self, w: int, h: int) -> None:
        # one plain number per gridline; anchors do the centring, no text measuring needed
        cx, cy = w / 2.0, h / 2.0
        for v in range(-100, 101, 20):
            if v == 0:
                continue
            x, _ = val_to_px(v, 0, w, h)
            self.create_text(x, cy + style.px(6), text=str(v), anchor="n", fill=style.COLOR_STATUS_TEXT, font=style.FONT_TICK)
            _, y = val_to_px(0, v, w, h)
            self.create_text(cx - style.px(8), y, text=str(v), anchor="e", fill=style.COLOR_STATUS_TEXT, font=style.FONT_TICK)

    def _draw_points(self) -> None:
        r, r_hover, r_dim = LAYOUT.point_radius, LAYOUT.point_radius_hover, LAYOUT.dim_radius
        gap = style.px(6)
        # dimmed (non-matching) points first so matches sit on top
        for p in sorted(self._points, key=lambda p: p["match"]):
            x, y, name = p["px"], p["py"], p["country"].name
            if not p["match"]:
                self.create_oval(x - r_dim, y - r_dim, x + r_dim, y + r_dim, fill=style.COLOR_POINT_DIM, outline="")
                continue
            if self._hovered is p:
                ring = r_hover + style.px(3)
                self.create_oval(x - ring, y - ring, x + ring, y + ring, outline=style.COLOR_POINT_HOVER_RING, width=2)
                self.create_oval(x - r_hover, y - r_hover, x + r_hover, y + r_hover, fill=style.COLOR_POINT_HOVER, outline="")
                label_y, color = y + r_hover + gap, style.COLOR_FG
            else:
                self.create_oval(x - r, y - r, x + r, y + r, fill=style.COLOR_POINT, outline="")
                label_y, color = y + r + gap, style.COLOR_STATUS_TEXT
            self.create_text(x, label_y, text=name, anchor="n", fill=color, font=style.FONT_COUNTRY_LABEL)

    def _draw_empty_note(self, w: int, h: int) -> None:
        text = f"No data for {self.year} yet." if self.year else "No data yet."
        self.create_text(w / 2, h / 2 - style.px(50), text=text, fill=style.COLOR_STATUS_TEXT, font=style.FONT_TITLE)
        self.create_text(w / 2, h / 2 - style.px(50) + style.px(28), text='Click "Data" below and add entries for a country.',
                         fill=style.COLOR_HINT, font=style.FONT_NORMAL)

    # -- hover ----------------------------------------------------------------------------

    def _on_motion(self, event) -> None:
        hovered = find_hovered(self._points, event.x, event.y)
        self.configure(cursor="hand2" if hovered else "")
        if hovered is not self._hovered:
            self._hovered = hovered
            self.redraw()
        self.delete("tip")
        if hovered is not None:
            self._draw_tooltip(hovered, event.x, event.y)

    def _on_leave(self, _event=None) -> None:
        self.delete("tip")
        if self._hovered is not None:
            self._hovered = None
            self.redraw()

    def _draw_tooltip(self, point: dict, mx: float, my: float) -> None:
        country, score = point["country"], point["score"]
        entries = store.entries(country.index, self.year)
        latest = entries[-1] if entries else None

        n = score.count
        lines = [
            (country.name, style.FONT_BOLD, style.COLOR_FG),
            (f"Left/Right: {fmt(score.left_right)} | Lib/Auth: {fmt(score.lib_auth)}", style.FONT_NORMAL, style.COLOR_STATUS_TEXT),
            (f"Average of {n} entries" if n > 1 else "1 entry", style.FONT_NORMAL, style.COLOR_HINT),
        ]
        if latest is not None:
            lines.append((latest.summary or "No summary available.", style.FONT_NORMAL, style.COLOR_FG))
            detail = " \u2022 ".join(filter(None, (latest.justification_lr, latest.justification_la)))
            lines.append((detail or "No details available.", style.FONT_NORMAL, style.COLOR_STATUS_TEXT))

        pad, width = LAYOUT.tooltip_padding, LAYOUT.tooltip_width
        items, y = [], 0
        for text, font, color in lines:                 # stack the lines at (0, 0) first to learn the height
            item = self.create_text(0, y, text=text, font=font, fill=color, anchor="nw", width=width - 2 * pad, tags="tip")
            x0, y0, x1, y1 = self.bbox(item)
            items.append(item)
            y = y1 + style.px(3)
        total_h = y + 2 * pad

        cw, ch = self.winfo_width(), self.winfo_height()
        tx = max(5, min(mx + 15, cw - width - 10))
        ty = max(5, min(my + 15, ch - total_h - 10))
        for item in items:
            self.move(item, tx + pad, ty + pad)
        box = self.create_rectangle(tx, ty, tx + width, ty + total_h, fill=style.COLOR_TOOLTIP_BG,
                                    outline=style.COLOR_TOOLTIP_BORDER, tags="tip")
        self.tag_lower(box, items[0])
