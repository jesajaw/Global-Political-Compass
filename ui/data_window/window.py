"""
The DATA window: pick a country, work on its entries.

    left:   search box + list of ALL countries (the ones that already have data are highlighted)
    right:  the selected country's entries, grouped by year -- a year holds any number of entries and
            its row shows their average (that average is exactly what the compass plots, see
            data.scoring.get_score) -- plus a form to add a new entry, adjust or delete the selected
            one, or let the agent evaluate the country for a year.

No file access and no maths in here: reading/writing goes through data.store, averaging through
data.scoring, the LLM through agent. This module only builds widgets and moves values between them.

DataView is the content; DataWindow wraps it in a Toplevel for the main app, and the repo-root
data_editor.py packs the same DataView straight into its own root window.
"""

from __future__ import annotations

import queue
import re
import threading
import tkinter as tk
from datetime import date
from tkinter import ttk

import agent
from data import scoring, store
from .. import dialogs, style
from ..compass_window.view import fmt
from ..style import LAYOUT
from ..widgets import Cell, HintEntry, ToolWindow

_YEAR_RE = re.compile(r"^\d{4}$")


class ScoreField(ttk.Frame):
    """A -100..+100 value: slider and number box kept in sync."""

    def __init__(self, parent):
        super().__init__(parent)
        self._var = tk.StringVar(value="0")
        self._syncing = False
        self._scale = ttk.Scale(self, from_=-100, to=100, orient="horizontal", command=self._from_scale)
        self._scale.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Spinbox(self, from_=-100, to=100, width=5, textvariable=self._var).pack(side="left")
        self._var.trace_add("write", self._from_var)

    def _from_scale(self, value) -> None:
        if self._syncing:
            return
        self._syncing = True
        self._var.set(str(round(float(value))))
        self._syncing = False

    def _from_var(self, *_args) -> None:
        if self._syncing:
            return
        try:
            number = int(self._var.get())
        except ValueError:
            return                                # half-typed text, e.g. "-"
        self._syncing = True
        self._scale.set(number)
        self._syncing = False

    def value(self, label: str) -> int:
        try:
            return int(self._var.get())
        except ValueError:
            raise ValueError(f"{label} must be a whole number between -100 and 100.")

    def set(self, number: int) -> None:
        self._var.set(str(number))


class DataView(ttk.Frame):
    def __init__(self, parent, on_data_changed, padding: int = 0):
        super().__init__(parent, padding=padding)
        self.on_data_changed = on_data_changed
        self._country = None                       # data.Country | None
        self._shown: list = []                     # countries currently in the list box
        self._editing_id: str | None = None        # None = the form creates a new entry
        self._busy = False                         # an agent request is running

        self._build_left()
        self._build_right()
        self._fill_list("")
        self._new_entry()

    # -- construction -----------------------------------------------------------------

    def _build_left(self) -> None:
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(0, 12))

        self.search = HintEntry(left, "Search country...", on_change=self._fill_list, width=30)
        self.search.pack(fill="x", ipady=4, pady=(0, 8))

        box = ttk.Frame(left)
        box.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(box, exportselection=False, width=30)
        style.style_listbox(self.listbox)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self._on_country_select)

    def _build_right(self) -> None:
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True)

        self.title_label = ttk.Label(right, text="Select a country", style="Title.TLabel")
        self.title_label.pack(anchor="w")
        self.info_label = ttk.Label(right, text="Pick a country on the left to see and add its entries.", style="Note.TLabel")
        self.info_label.pack(anchor="w", pady=(0, 8))

        # entries, grouped by year
        tree_box = ttk.Frame(right)
        tree_box.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_box, columns=("lr", "la", "info", "origin"), selectmode="browse", height=8)
        for column, title, width, anchor in (
            ("#0", "Year / Entry", 170, "w"), ("lr", "Left/Right", 80, "center"), ("la", "Lib/Auth", 80, "center"),
            ("info", "Summary", 220, "w"), ("origin", "Origin", 70, "center"),
        ):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=style.px(width), anchor=anchor, stretch=column == "info")
        self.tree.tag_configure("year", font=style.FONT_BOLD)
        scroll = ttk.Scrollbar(tree_box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # the form
        self.form = ttk.LabelFrame(right, text="New entry", padding=10)
        self.form.pack(fill="x", pady=(10, 8))
        self.form.columnconfigure(1, weight=1)

        self.year_entry = ttk.Entry(self.form, width=8)
        self.lr_field = ScoreField(self.form)
        self.la_field = ScoreField(self.form)
        self.summary_entry = ttk.Entry(self.form)
        self.just_lr = tk.Text(self.form, height=2, width=10)
        self.just_la = tk.Text(self.form, height=2, width=10)
        self.sources = tk.Text(self.form, height=2, width=10)
        for text in (self.just_lr, self.just_la, self.sources):
            style.style_text(text)

        rows = (
            ("Year", self.year_entry), ("Left / Right", self.lr_field), ("Lib / Auth", self.la_field),
            ("Summary", self.summary_entry), ("Justification L/R", self.just_lr),
            ("Justification Lib/Auth", self.just_la), ("Sources (one per line)", self.sources),
        )
        for row, (label, widget) in enumerate(rows):
            ttk.Label(self.form, text=label).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=3)
            widget.grid(row=row, column=1, sticky="w" if widget is self.year_entry else "ew", pady=3)

        # action tiles
        buttons = ttk.Frame(right)
        buttons.pack(fill="x")
        h = LAYOUT.control_height
        for title, command, width in (
            ("New", self._new_entry, 70), ("Save", self._save, 70), ("Delete", self._delete, 80),
            ("Evaluate (Agent)", self._evaluate, 160),
        ):
            Cell(buttons, title, on_click=command, width=style.px(width), height=h).pack(side="left", padx=(0, 8))
        self.status = ttk.Label(right, text="", style="Note.TLabel")
        self.status.pack(anchor="w", pady=(8, 0))

    # -- country list ---------------------------------------------------------------------

    def _fill_list(self, query: str = "") -> None:
        query = query.lower().strip()
        self._shown = [c for c in store.countries() if query in c.name.lower()]
        self.listbox.delete(0, "end")
        for i, country in enumerate(self._shown):
            n = store.entry_count(country.index)
            self.listbox.insert("end", f"{country.name}   ({n})" if n else country.name)
            if n:
                self.listbox.itemconfig(i, fg=style.COLOR)        # countries that already have data stand out
        if self._country is not None and self._country in self._shown:
            i = self._shown.index(self._country)
            self.listbox.selection_set(i)
            self.listbox.see(i)

    def _on_country_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if not selection or self._busy:
            return
        self._country = self._shown[selection[0]]
        self._editing_id = None
        self._show_country()
        self._new_entry()

    def _show_country(self, select_id: str | None = None) -> None:
        country = self._country
        self.title_label.configure(text=country.name)
        n, years = store.entry_count(country.index), len(store.years_of(country.index))
        if n:
            self.info_label.configure(text=f"{n} {'entry' if n == 1 else 'entries'} in {years} {'year' if years == 1 else 'years'}. "
                                           "A year's row shows the average of its entries.")
        else:
            self.info_label.configure(text="No entries yet. This country's file is created when you save the first one.")

        self.tree.delete(*self.tree.get_children())
        for year, score in scoring.yearly_scores(country.index).items():
            info = f"Average of {score.count} entries" if score.count > 1 else "1 entry"
            parent = self.tree.insert("", "end", iid=f"y:{year}", text=year, open=True, tags=("year",),
                                      values=(fmt(score.left_right), fmt(score.lib_auth), info, ""))
            for entry in store.entries(country.index, year):
                self.tree.insert(parent, "end", iid=entry.id, text=entry.id,
                                 values=(entry.left_right, entry.lib_auth, entry.summary, entry.origin))
        if select_id and self.tree.exists(select_id):
            self.tree.selection_set(select_id)
            self.tree.see(select_id)

    # -- tree selection <-> form ---------------------------------------------------------------

    def _on_tree_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection or self._country is None:
            return
        iid = selection[0]
        if iid.startswith("y:"):
            self._new_entry(year=iid[2:])           # clicking a year: ready to add another entry to it
            return
        year = self.tree.parent(iid)[2:]
        entry = next((e for e in store.entries(self._country.index, year) if e.id == iid), None)
        if entry is not None:
            self._fill_form(entry, year)

    def _fill_form(self, entry, year: str) -> None:
        self._editing_id = entry.id
        self.form.configure(text=f"Edit entry {entry.id}")
        self.year_entry.delete(0, "end")
        self.year_entry.insert(0, year)
        self.lr_field.set(entry.left_right)
        self.la_field.set(entry.lib_auth)
        self.summary_entry.delete(0, "end")
        self.summary_entry.insert(0, entry.summary)
        for widget, text in ((self.just_lr, entry.justification_lr), (self.just_la, entry.justification_la),
                             (self.sources, "\n".join(entry.sources))):
            widget.delete("1.0", "end")
            widget.insert("1.0", text)

    def _new_entry(self, year: str | None = None) -> None:
        """Empty the form so that Save creates a NEW entry (keeps the year, so several entries per year are quick)."""
        if year is None:
            year = self.year_entry.get().strip() or str(date.today().year)
        self._editing_id = None
        self.form.configure(text="New entry")
        if self.tree.selection():
            self.tree.selection_remove(*self.tree.selection())
        self.year_entry.delete(0, "end")
        self.year_entry.insert(0, year)
        self.lr_field.set(0)
        self.la_field.set(0)
        self.summary_entry.delete(0, "end")
        for widget in (self.just_lr, self.just_la, self.sources):
            widget.delete("1.0", "end")

    def _read_form(self) -> dict:
        return dict(
            year=self.year_entry.get().strip(),
            left_right=self.lr_field.value("Left / Right"),
            lib_auth=self.la_field.value("Lib / Auth"),
            summary=self.summary_entry.get(),
            justification_lr=self.just_lr.get("1.0", "end"),
            justification_la=self.just_la.get("1.0", "end"),
            sources=self.sources.get("1.0", "end").splitlines(),
        )

    # -- actions ------------------------------------------------------------------------------------

    def _error(self, title: str, message: str) -> None:
        dialogs.show_error(self.winfo_toplevel(), title, message)

    def _after_change(self, select_id: str | None = None) -> None:
        self._fill_list(self.search.value())
        self._show_country(select_id)
        self.on_data_changed()

    def _save(self) -> None:
        if self._country is None:
            return self._error("No country", "Select a country on the left first.")
        try:
            fields = self._read_form()
            cid = self._country.index
            if self._editing_id:
                entry = store.update_entry(cid, self._editing_id, **fields)
            else:
                entry = store.add_entry(cid, fields.pop("year"), fields.pop("left_right"), fields.pop("lib_auth"), **fields)
        except (ValueError, KeyError) as e:
            return self._error("Could not save", str(e.args[0] if isinstance(e, KeyError) else e))
        self.status.configure(text=f"Saved {entry.id}.")
        self._after_change(select_id=entry.id)

    def _delete(self) -> None:
        if self._country is None or not self._editing_id:
            return self._error("Nothing selected", "Select an entry in the list first.")
        if not dialogs.ask_yes_no(self.winfo_toplevel(), "Delete entry", f"Delete entry {self._editing_id}?"):
            return
        try:
            store.delete_entry(self._country.index, self._editing_id)
        except KeyError as e:
            return self._error("Could not delete", str(e.args[0]))
        self.status.configure(text=f"Deleted {self._editing_id}.")
        self._editing_id = None
        self._after_change()
        self._new_entry()

    # -- agent ---------------------------------------------------------------------------------------

    def _evaluate(self) -> None:
        if self._busy:
            return
        if self._country is None:
            return self._error("No country", "Select a country on the left first.")
        year = self.year_entry.get().strip()
        if not _YEAR_RE.match(year):
            return self._error("Invalid year", "Enter a four-digit year (e.g. 2024) in the form first.")

        self._busy = True
        self.status.configure(text=f"Asking the model about {self._country.name} {year} ... this can take a few minutes.")
        results: queue.Queue = queue.Queue()
        country = self._country

        def work() -> None:                          # runs in a thread: NO tk calls in here
            try:
                results.put(("ok", agent.evaluate_country(country.name, year)))
            except agent.AgentError as e:
                results.put(("error", str(e)))
            except Exception as e:
                results.put(("error", f"Unexpected error: {e}"))

        threading.Thread(target=work, daemon=True).start()
        self.after(300, lambda: self._poll_agent(results, country, year))

    def _poll_agent(self, results: queue.Queue, country, year: str) -> None:
        if not self.winfo_exists():
            return                                   # window was closed while waiting
        try:
            kind, payload = results.get_nowait()
        except queue.Empty:
            self.after(300, lambda: self._poll_agent(results, country, year))
            return

        self._busy = False
        if kind == "error":
            self.status.configure(text="The agent request failed.")
            return self._error("Agent failed", payload)
        try:
            entry = agent.store_result(country.index, year, payload)   # stored here, in the main thread
        except ValueError as e:
            return self._error("Could not save", str(e))
        self.status.configure(text=f"Agent entry {entry.id} added.")
        if self._country == country:
            self._editing_id = None
            self._after_change(select_id=entry.id)
        else:
            self._fill_list(self.search.value())
            self.on_data_changed()


class DataWindow(ToolWindow):
    def __init__(self, parent, on_data_changed):
        super().__init__(parent, "Data", size=LAYOUT.data_window_size)
        self.minsize(style.px(820), style.px(600))
        DataView(self.content, on_data_changed).pack(fill="both", expand=True)
