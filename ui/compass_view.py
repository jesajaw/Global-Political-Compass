"""
Pure rendering for the compass canvas: grid, axes, country points, hover
tooltip. Takes the app's current state (countries/scores/evaluations,
selected year, search query) and draws into the given drawlist -- no
widget construction, no data loading here, just draw_* calls.
"""

from __future__ import annotations

import math

import dearpygui.dearpygui as dpg

import theme
from theme import LAYOUT


def val_to_px(left_right: float, lib_auth: float, w: int, h: int) -> tuple[float, float]:
    pad = LAYOUT.padding
    x = pad + ((left_right + 100) / 200.0) * (w - 2 * pad)
    y = pad + ((100 - lib_auth) / 200.0) * (h - 2 * pad)
    return x, y


def _draw_quadrant_labels(drawlist: str, w: int, h: int) -> None:
    pad = LAYOUT.padding
    labels = {
        (pad + 10, pad + 10): "AUTHORITARIAN LEFT",
        (w - pad - 165, pad + 10): "AUTHORITARIAN RIGHT",
        (pad + 10, h - pad - 22): "LIBERTARIAN LEFT",
        (w - pad - 150, h - pad - 22): "LIBERTARIAN RIGHT",
    }
    for pos, text in labels.items():
        dpg.draw_text(pos, text, color=theme.COLOR_QUADRANT_LABEL, parent=drawlist)


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

    dpg.draw_text((pad + 5, cy - 18), "LEFT (-100)", color=theme.COLOR_FG, parent=drawlist)
    dpg.draw_text((w - pad - 80, cy - 18), "RIGHT (+100)", color=theme.COLOR_FG, parent=drawlist)
    dpg.draw_text((cx - 65, pad + 5), "AUTHORITARIAN (+100)", color=theme.COLOR_FG, parent=drawlist)
    dpg.draw_text((cx - 55, h - pad - 20), "LIBERTARIAN (-100)", color=theme.COLOR_FG, parent=drawlist)


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

    code = f"[{country['code']}] " if country.get("code") else ""
    dpg.draw_text((tx + 10, ty + 8), f"{code}{country['name']}", color=theme.COLOR_FG, parent=drawlist)

    coords = f"Left/Right: {score['left_right']} | Lib/Auth: {score['lib_auth']}"
    dpg.draw_text((tx + 10, ty + 28), coords, color=theme.COLOR_STATUS_TEXT, parent=drawlist)

    summary = eval_info.get("summary", "No summary available.")
    dpg.draw_text((tx + 10, ty + 48), summary, color=theme.COLOR_FG, parent=drawlist)

    just = eval_info.get("justification", {})
    detail = " \u2022 ".join(filter(None, (just.get("left_right"), just.get("lib_auth")))) or "No details available."
    if len(detail) > 42:
        detail = detail[:39] + "..."
    dpg.draw_text((tx + 10, ty + 70), detail, color=theme.COLOR_STATUS_TEXT, parent=drawlist)


def draw_compass(drawlist: str, countries: list, scores: dict, evaluations: dict, year: str, search_query: str) -> None:
    dpg.delete_item(drawlist, children_only=True)

    w = dpg.get_item_width(drawlist)
    h = dpg.get_item_height(drawlist)
    if not w or not h or w <= 0 or h <= 0:
        return

    _draw_quadrant_labels(drawlist, w, h)
    _draw_grid(drawlist, w, h)
    _draw_axes(drawlist, w, h)

    # get_item_rect_min gives the drawlist's actual on-screen origin, so the
    # hover hit-test stays correct once the canvas resizes with the window
    # (the original used get_item_state(...)["pos"], which drifted).
    rect_min = dpg.get_item_rect_min(drawlist)
    mouse = dpg.get_mouse_pos(local=False)
    rel_mx, rel_my = mouse[0] - rect_min[0], mouse[1] - rect_min[1]

    points = []
    hovered = None
    for country in countries:
        score = scores.get(str(country["index"]), {}).get(year)
        if not score:
            continue
        matches = not search_query or search_query in country["name"].lower()
        px, py = val_to_px(score["left_right"], score["lib_auth"], w, h)
        point = {"country": country, "score": score, "px": px, "py": py, "match": matches}
        points.append(point)
        if matches and math.hypot(rel_mx - px, rel_my - py) < LAYOUT.hover_hit_distance:
            hovered = point

    # draw dimmed/non-matching points first so matches sit on top
    points.sort(key=lambda p: p["match"])

    for p in points:
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
            dpg.draw_text((px - 20, py + 16), p["country"]["name"], color=theme.COLOR_FG, parent=drawlist)
        else:
            dpg.draw_circle((px, py), LAYOUT.point_radius, color=theme.COLOR_POINT, fill=theme.COLOR_POINT,
                             parent=drawlist)
            dpg.draw_text((px - 18, py + 14), p["country"]["name"], color=theme.COLOR_STATUS_TEXT, parent=drawlist)

    if hovered:
        _draw_tooltip(drawlist, hovered, rel_mx, rel_my, w, h, evaluations)
