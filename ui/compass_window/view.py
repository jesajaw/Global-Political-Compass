"""
Rendering for the compass canvas: grid, axes, country points, hover
tooltip. No zoom/pan -- the default 80%-of-screen view is the only view, so
point/label sizes (theme.LAYOUT.point_radius*, *_label_size) are tuned to
read clearly on their own.

Split into stages on purpose, so the window can avoid redrawing every
single frame (recreating ~20+ draw items 60x/second caused visible
flicker/jank):

  - compute_visible_points() / find_hovered() are cheap, pure calculations
    (no dpg.draw_* calls) run every frame to check whether anything
    actually changed (mouse moved onto a new country, etc).
  - draw_compass() does the actual (comparatively expensive) drawing, and
    is only called when that check says something did change.

CompassCanvas ties those two stages together and owns the "did anything
change since last frame" cache, so compass_window/window.py only has to
call canvas.render(...) once per frame -- it doesn't touch drawing or
caching details itself.
"""

from __future__ import annotations

import math

import dearpygui.dearpygui as dpg

from .. import theme
from ..theme import LAYOUT


def val_to_px(left_right: float, lib_auth: float, w: int, h: int) -> tuple[float, float]:
    pad = LAYOUT.padding
    x = pad + ((left_right + 100) / 200.0) * (w - 2 * pad)
    y = pad + ((100 - lib_auth) / 200.0) * (h - 2 * pad)
    return x, y


def compute_visible_points(countries: list, scores: dict, year: str, search_query: str, w: int, h: int) -> list:
    points = []
    for country in countries:
        score = scores.get(str(country["index"]), {}).get(year)
        if not score:
            continue
        matches = not search_query or search_query in country["name"].lower()
        px, py = val_to_px(score["left_right"], score["lib_auth"], w, h)
        points.append({"country": country, "score": score, "px": px, "py": py, "match": matches})
    return points


def find_hovered(points: list, rel_mx: float, rel_my: float) -> dict | None:
    hovered = None
    for p in points:
        if p["match"] and math.hypot(rel_mx - p["px"], rel_my - p["py"]) < LAYOUT.hover_hit_distance:
            hovered = p
    return hovered


def _draw_quadrant_labels(drawlist: str, w: int, h: int) -> None:
    pad = LAYOUT.padding
    size = LAYOUT.quadrant_label_size
    # widths below are rough char-count * size/1.8 estimates so the
    # right-aligned labels don't run past the frame at any UI_SCALE
    labels = {
        (pad + 10, pad + 10): "AUTHORITARIAN LEFT",
        (w - pad - 19 * size * 0.62, pad + 10): "AUTHORITARIAN RIGHT",
        (pad + 10, h - pad - size - 8): "LIBERTARIAN LEFT",
        (w - pad - 17 * size * 0.62, h - pad - size - 8): "LIBERTARIAN RIGHT",
    }
    for pos, text in labels.items():
        dpg.draw_text(pos, text, color=theme.COLOR_QUADRANT_LABEL, size=size, parent=drawlist)


def _draw_grid(drawlist: str, w: int, h: int) -> None:
    pad = LAYOUT.padding
    for i in range(-80, 90, 20):
        if i == 0:
            continue
        px, py = val_to_px(i, i, w, h)
        dpg.draw_line((px, pad), (px, h - pad), color=theme.COLOR_GRID, thickness=1, parent=drawlist)
        dpg.draw_line((pad, py), (w - pad, py), color=theme.COLOR_GRID, thickness=1, parent=drawlist)


def _draw_axes(drawlist: str, w: int, h: int) -> None:
    pad = LAYOUT.padding
    cx, cy = w / 2.0, h / 2.0
    dpg.draw_line((cx, pad), (cx, h - pad), color=theme.COLOR_AXIS, thickness=1.5, parent=drawlist)
    dpg.draw_line((pad, cy), (w - pad, cy), color=theme.COLOR_AXIS, thickness=1.5, parent=drawlist)


def _draw_axis_ticks(drawlist: str, w: int, h: int) -> None:
    # plain numbers instead of "LEFT (-100)" / "AUTHORITARIAN (+100)" style
    # text -- one tick per gridline, small and unobtrusive
    size = LAYOUT.tick_label_size
    char_w = size * 0.56
    cx, cy = w / 2.0, h / 2.0

    for v in range(-100, 101, 20):
        if v == 0:
            continue  # would collide with the "0" drawn on the y-axis below
        x, _ = val_to_px(v, 0, w, h)
        label = str(v)
        dpg.draw_text((x - len(label) * char_w / 2, cy + 6), label,
                      color=theme.COLOR_STATUS_TEXT, size=size, parent=drawlist)

    for v in range(-100, 101, 20):
        _, y = val_to_px(0, v, w, h)
        label = str(v)
        dpg.draw_text((cx - len(label) * char_w - 8, y - size / 2), label,
                      color=theme.COLOR_STATUS_TEXT, size=size, parent=drawlist)


def _draw_tooltip(drawlist: str, point: dict, mx: float, my: float, w: int, h: int, evaluations: dict) -> None:
    country, score = point["country"], point["score"]
    eval_info = evaluations.get("evaluations", {}).get(score.get("rubric_id"), {})

    card_w, card_h = LAYOUT.tooltip_w, LAYOUT.tooltip_h
    tx = min(mx + 15, w - card_w - 10)
    ty = min(my + 15, h - card_h - 10)

    dpg.draw_rectangle(
        (tx, ty), (tx + card_w, ty + card_h),
        color=theme.COLOR_TOOLTIP_BORDER, fill=theme.COLOR_TOOLTIP_BG,
        rounding=5, thickness=1, parent=drawlist,
    )

    title_size = LAYOUT.tooltip_title_size
    text_size = LAYOUT.tooltip_text_size
    line = title_size + 6
    max_chars = round(card_w / (text_size * 0.58))

    code = f"[{country['code']}] " if country.get("code") else ""
    dpg.draw_text((tx + 12, ty + 8), f"{code}{country['name']}", color=theme.COLOR_FG,
                  size=title_size, parent=drawlist)

    coords = f"Left/Right: {score['left_right']} | Lib/Auth: {score['lib_auth']}"
    dpg.draw_text((tx + 12, ty + 8 + line), coords, color=theme.COLOR_STATUS_TEXT,
                  size=text_size, parent=drawlist)

    summary = eval_info.get("summary", "No summary available.")
    if len(summary) > max_chars:
        summary = summary[:max_chars - 3] + "..."
    dpg.draw_text((tx + 12, ty + 8 + 2 * line), summary, color=theme.COLOR_FG,
                  size=text_size, parent=drawlist)

    just = eval_info.get("justification", {})
    detail = " \u2022 ".join(filter(None, (just.get("left_right"), just.get("lib_auth")))) or "No details available."
    if len(detail) > max_chars:
        detail = detail[:max_chars - 3] + "..."
    dpg.draw_text((tx + 12, ty + 8 + 3 * line), detail, color=theme.COLOR_STATUS_TEXT,
                  size=text_size, parent=drawlist)


def draw_compass(
    drawlist: str, w: int, h: int, points: list, hovered: dict | None,
    evaluations: dict, rel_mx: float, rel_my: float,
) -> None:
    dpg.delete_item(drawlist, children_only=True)

    _draw_quadrant_labels(drawlist, w, h)
    _draw_grid(drawlist, w, h)
    _draw_axes(drawlist, w, h)
    _draw_axis_ticks(drawlist, w, h)

    # draw dimmed/non-matching points first so matches sit on top
    for p in sorted(points, key=lambda p: p["match"]):
        px, py = p["px"], p["py"]
        is_hovered = hovered is not None and hovered["country"]["index"] == p["country"]["index"]

        if not p["match"]:
            dpg.draw_circle((px, py), 2.5, color=theme.COLOR_POINT_DIM, fill=theme.COLOR_POINT_DIM, parent=drawlist)
            continue

        if is_hovered:
            dpg.draw_circle((px, py), LAYOUT.point_radius_hover + 3, color=theme.COLOR_POINT_HOVER_RING,
                             thickness=1.5, parent=drawlist)
            dpg.draw_circle((px, py), LAYOUT.point_radius_hover, color=theme.COLOR_POINT_HOVER,
                             fill=theme.COLOR_POINT_HOVER, parent=drawlist)
            name_size = LAYOUT.country_label_size
            dpg.draw_text((px - len(p["country"]["name"]) * name_size * 0.28, py + LAYOUT.point_radius_hover + 6),
                          p["country"]["name"], color=theme.COLOR_FG, size=name_size, parent=drawlist)
        else:
            dpg.draw_circle((px, py), LAYOUT.point_radius, color=theme.COLOR_POINT, fill=theme.COLOR_POINT,
                             parent=drawlist)
            name_size = LAYOUT.country_label_size
            dpg.draw_text((px - len(p["country"]["name"]) * name_size * 0.26, py + LAYOUT.point_radius + 6),
                          p["country"]["name"], color=theme.COLOR_STATUS_TEXT, size=name_size, parent=drawlist)

    if hovered:
        _draw_tooltip(drawlist, hovered, rel_mx, rel_my, w, h, evaluations)


class CompassCanvas:
    """
    Owns one drawlist: computing the visible points, hit-testing the mouse
    against them, and (only when something actually changed) redrawing.

    compass_window/window.py just constructs one of these against its
    drawlist tag and calls .render(...) once per frame -- it doesn't touch
    compute_visible_points/find_hovered/draw_compass or the "did anything
    change" cache directly anymore.
    """

    def __init__(self, drawlist_tag: str):
        self.tag = drawlist_tag
        self._last_render_key = None

    def render(self, countries: list, scores: dict, evaluations: dict, year: str, search_query: str) -> None:
        w = dpg.get_item_width(self.tag)
        h = dpg.get_item_height(self.tag)
        if not w or not h or w <= 0 or h <= 0:
            return

        points = compute_visible_points(countries, scores, year, search_query, w, h)

        rect_min = dpg.get_item_rect_min(self.tag)
        mouse = dpg.get_mouse_pos(local=False)
        rel_mx, rel_my = mouse[0] - rect_min[0], mouse[1] - rect_min[1]
        hovered = find_hovered(points, rel_mx, rel_my)
        hovered_id = hovered["country"]["index"] if hovered else None

        # only pay for the actual (comparatively expensive) draw when
        # something that affects the picture changed since last frame --
        # most frames nothing does, so most frames draw nothing at all.
        # Mouse position only matters for the render while something is
        # actually hovered (it moves the tooltip) -- otherwise moving the
        # mouse across empty canvas would force a redraw every frame again.
        mouse_component = (round(rel_mx), round(rel_my)) if hovered_id is not None else None
        render_key = (year, search_query, w, h, hovered_id, mouse_component)
        if render_key == self._last_render_key:
            return
        self._last_render_key = render_key

        draw_compass(self.tag, w, h, points, hovered, evaluations, rel_mx, rel_my)
