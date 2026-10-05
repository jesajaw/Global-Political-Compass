"""
Tiny stand-in for tkinter so ui/ code can be constructed and driven headlessly, without a
display or a tkinter installation -- see tests/README.md. Used only by test_ui.py, never by the
app itself.
"""
import sys, types

class _Var:
    def __init__(self, master=None, value=""): self._v = value; self._tr = []
    def get(self): return self._v
    def set(self, v):
        self._v = v
        for cb in list(self._tr): cb()
    def trace_add(self, mode, cb): self._tr.append(lambda: cb())
StringVar = _Var
class BooleanVar(_Var):
    def __init__(self, master=None, value=False): super().__init__(master, value)
    def get(self): return bool(self._v)

class Widget:
    def __init__(self, master=None, *a, **k):
        self.master = master; self.opts = dict(k); self.children = []; self.binds = {}
        self._text = ""; self._exists = True
        if master is not None and hasattr(master, "children"): master.children.append(self)
    def configure(self, *a, **k):
        if a and isinstance(a[0], dict): k = a[0]
        self.opts.update(k)
    config = configure
    def cget(self, k): return self.opts.get(k)
    def __getitem__(self, k): return self.opts.get(k)
    def bind(self, seq, fn, add=None): self.binds[seq] = fn
    def winfo_exists(self): return self._exists
    def winfo_toplevel(self): return self
    def winfo_children(self): return list(self.children)
    def winfo_width(self): return 1000
    def winfo_height(self): return 700
    def winfo_rootx(self): return 0
    def winfo_rooty(self): return 0
    def winfo_id(self): return 1
    def winfo_screenwidth(self): return 1920
    def winfo_screenheight(self): return 1080
    def after(self, ms, fn=None): (_pending.append(fn) if fn else None)
    def destroy(self): self._exists = False
    def __getattr__(self, name):           # pack/grid/lift/title/... -> harmless no-ops
        if name.startswith("__"): raise AttributeError(name)
        return lambda *a, **k: None
_pending = []

class Tk(Widget):
    def mainloop(self): pass
class Toplevel(Widget):
    def wait_window(self, w=None): pass
class Frame(Widget): pass
class Label(Widget): pass
class Button(Widget): pass
class Entry(Widget):
    def __init__(self, *a, **k): super().__init__(*a, **k); self._text = ""
    def get(self): return self._text
    def delete(self, a, b=None): self._text = ""
    def insert(self, i, s): self._text = self._text[:0] + s if i == 0 else self._text + s
class Text(Widget):
    def __init__(self, *a, **k): super().__init__(*a, **k); self._text = ""
    def get(self, a, b=None): return self._text + "\n"
    def delete(self, a, b=None): self._text = ""
    def insert(self, i, s): self._text = s
class Listbox(Widget):
    def __init__(self, *a, **k): super().__init__(*a, **k); self.items = []; self.sel = ()
    def delete(self, a, b=None): self.items = []; self.sel = ()
    def insert(self, i, s): self.items.append(s)
    def curselection(self): return self.sel
    def selection_set(self, i): self.sel = (i,)
class Canvas(Widget):
    def __init__(self, *a, **k): super().__init__(*a, **k); self.items = []; self._n = 0
    def _mk(self, kind, args, kw):
        self._n += 1; self.items.append((self._n, kind, args, kw)); return self._n
    def create_text(self, *a, **k): return self._mk("text", a, k)
    def create_line(self, *a, **k): return self._mk("line", a, k)
    def create_oval(self, *a, **k): return self._mk("oval", a, k)
    def create_rectangle(self, *a, **k): return self._mk("rect", a, k)
    def delete(self, tag): self.items = [] if tag == "all" else [i for i in self.items if i[3].get("tags") != tag]
    def bbox(self, item): return (0, 0, 100, 18)
class Scale: pass

ttk = types.ModuleType("tkinter.ttk")
class _Tree(Widget):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.nodes = {}; self.order = []; self.sel = ()
    def get_children(self, item=""): return tuple(i for i in self.order if self.nodes[i]["parent"] == item)
    def delete(self, *items):
        for i in items:
            for child in self.get_children(i): self.delete(child)   # real Tk removes descendants too
            self.nodes.pop(i, None); self.order = [o for o in self.order if o != i]
    def insert(self, parent, index, iid=None, **k):
        self.nodes[iid] = dict(parent=parent, **k); self.order.append(iid); return iid
    def exists(self, iid): return iid in self.nodes
    def parent(self, iid): return self.nodes[iid]["parent"]
    def selection(self): return self.sel
    def selection_set(self, iid): self.sel = (iid,)
    def selection_remove(self, *items): self.sel = ()
class _Scale(Widget):
    def __init__(self, *a, command=None, **k): super().__init__(*a, **k); self.command = command; self.val = 0
    def set(self, v): self.val = v; (self.command(v) if self.command else None)
class _Style:
    def __init__(self, root=None): pass
    def __getattr__(self, n): return lambda *a, **k: None
for name in ("Frame", "Label", "Button", "Entry", "Combobox", "Spinbox", "Scrollbar", "LabelFrame", "Checkbutton"):
    setattr(ttk, name, type(name, (Widget,), {}))
ttk.Entry = type("Entry", (Entry,), {}); ttk.Treeview = _Tree; ttk.Scale = _Scale; ttk.Style = _Style
sys.modules["tkinter.ttk"] = ttk


filedialog = types.ModuleType("tkinter.filedialog")
filedialog.asksaveasfilename = lambda **k: ""    # tests override this per-case
sys.modules["tkinter.filedialog"] = filedialog
