"""
Reusable building blocks, same idea as mtools' widgets.py:
- Cell: a clickable tile (title, optional status line, hover highlight) -- every button-like thing in the app is made from it
- ToolWindow: a themed Toplevel with a `self.content` frame that subclasses fill
- HintEntry: an entry that shows a grey hint text while it is empty (the "Search country..." boxes)
"""

import tkinter as tk
from tkinter import ttk

from . import style


class Cell(ttk.Frame):
    """
    A clickable tile: title, optional description/status line, hover highlight
    optional:
    - status_text is the description line: Leave it out (None, the default) for a cell that never shows one
    - on_click: leave it out for a plain, inert status tile (no hover, no click cursor, nothing bound)
    - extra_button: render an extra button (text, command) in the cell's corner
    """
    def __init__(self, parent, title: str, on_click=None, status_text: str | None = None, width: int = style.CELL_WIDTH, height: int = style.CELL_HEIGHT, extra_button=None):
        super().__init__(parent, padding=8, relief="groove", style="Cell.TFrame")
        wraplength = width - 20
        self.on_click = on_click
        self.pack_propagate(False)
        self.configure(width=width, height=height)

        self.title_label = ttk.Label(self, text=title, style="CellTitle.TLabel")
        self.title_label.pack(anchor="w")

        self.status_label = None
        clickable = [self, self.title_label]
        if status_text is not None:
            self.status_label = ttk.Label(self, text=status_text, style="Status.TLabel", wraplength=wraplength, justify="left")
            self.status_label.pack(anchor="w", pady=(4, 8), fill="x")
            clickable.append(self.status_label)

        if on_click is not None:
            for w in clickable:
                w.configure(cursor="hand2")
                w.bind("<Button-1>", self._on_click)
                w.bind("<Enter>", self._on_enter)
                w.bind("<Leave>", self._on_leave)

        if extra_button:
            text, command = extra_button
            ttk.Button(self, text=text, command=command).pack(anchor="e")

        self.bind("<Configure>", self._on_resize)

    def set_title(self, text: str) -> None:
        self.title_label.configure(text=text)

    def set_status(self, text: str) -> None:
        if self.status_label is not None:
            self.status_label.configure(text=text)

    def _on_click(self, _event=None) -> None:
        if self.on_click:
            self.on_click()

    def _on_enter(self, _event=None) -> None:
        self.configure(style="CellHover.TFrame")
        self.title_label.configure(style="CellTitleHover.TLabel")
        if self.status_label is not None:
            self.status_label.configure(style="StatusHover.TLabel")

    def _on_leave(self, _event=None) -> None:
        self.configure(style="Cell.TFrame")
        self.title_label.configure(style="CellTitle.TLabel")
        if self.status_label is not None:
            self.status_label.configure(style="Status.TLabel")

    def _on_resize(self, event) -> None:
        # Keep text reflowing with the cell's actual rendered width, not just its initial size.
        wrap = max(event.width - 20, 20)
        self.title_label.configure(wraplength=wrap)
        if self.status_label is not None:
            self.status_label.configure(wraplength=wrap)


class ToolWindow(tk.Toplevel):
    # Base window for a tool: themed Toplevel, title in the OS titlebar -- subclasses fill `self.content` with their own widgets/parameters.
    def __init__(self, parent, title: str, size: str = "420x360"):
        super().__init__(parent)
        self.title(title)
        self.geometry(size)
        self.minsize(340, 300)
        style.apply_style(self)

        self.content = ttk.Frame(self, padding=10)
        self.content.pack(fill="both", expand=True)

class HintEntry(ttk.Entry):
    """
    Entry with a grey placeholder. value() is always the real text ("" while the hint is showing);
    on_change(value) fires on every edit.
    """
    def __init__(self, parent, hint: str, on_change=None, width: int = 24):
        super().__init__(parent, width=width)
        self._hint = hint
        self._on_change = on_change
        self._showing_hint = False
        self._show_hint()
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        self.bind("<KeyRelease>", self._key_release)

    def value(self) -> str:
        return "" if self._showing_hint else self.get()

    def _show_hint(self) -> None:
        self._showing_hint = True
        self.delete(0, "end")
        self.insert(0, self._hint)
        self.configure(style="Hint.TEntry")

    def _focus_in(self, _event=None) -> None:
        if self._showing_hint:
            self.delete(0, "end")
            self._showing_hint = False
            self.configure(style="TEntry")

    def _focus_out(self, _event=None) -> None:
        if not self.get():
            self._show_hint()

    def _key_release(self, _event=None) -> None:
        if self._on_change is not None:
            self._on_change(self.value())
