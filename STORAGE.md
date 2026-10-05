# Storage & data model

Goal: whatever a tool from the README list produces -- a fit, an AFM scan, a PDE field, a complex FFT, a chain of
error-propagated results -- can be **saved, reloaded and traced back** without the tool author thinking about files.

## 1. Decision: SQLite + typed binary arrays + JSON where JSON is good

| | JSON only | SQLite project file (**chosen**) |
|---|---|---|
| 1024x1024 AFM grid | ~20 MB text, slow to parse | 8 MB raw, ~7 MB stored, loads in ~0.2 s |
| `NaN`, `inf`, complex (FFT, eigenvectors) | not valid JSON | exact |
| Crash while saving | truncated file = everything lost | atomic transaction, old state intact |
| "Which results came from this scan?" | read every file | one SQL query |
| Same x-axis in 10 derived datasets | stored 10x | stored once (content-addressed) |
| Corruption | silently wrong numbers | checksum error on load |
| New dependency | none | none (`sqlite3` is in the stdlib) |

So: the **project file** is the working store; **JSON** stays for what it is genuinely best at:

* `data/interchange.py` -- export one result, diff it in git, read it in an editor (`*.json`)
* `data/settings.py` -- preferences, presets, custom units (small, hand-editable)

The whole layout lives behind `data/codec.py`. It matches numpy's memory layout (little-endian, C order), so adding numpy
later needs no conversion of existing files.

## 2. Layers

```
tool ──> DataSet (dataset.py, in memory)
           │  store.add()  (store.py: workspace history, optional write-through)
           ▼
        Project (project.py) ──> codec.py ──> *.mtools  (SQLite file)
        interchange.py ────────> codec.py ──> *.json    (export/import)
        settings.py ───────────> codec.py ──> settings.json (per user)
```

## 3. The file (`*.mtools`)

One SQLite database, no side files (no WAL), `application_id` = "mTLS", schema version in `PRAGMA user_version`.

| Table | One row per | Notes |
|---|---|---|
| `meta` | key | format, created_at, anything project-wide (`set_meta`) |
| `datasets` | DataSet | `seq` (history order), `id`, `name`, `source_tool`, `created_at`, `params` (JSON), `metadata` (JSON) |
| `arrays` | DataArray | `bucket` = `data`\|`axes`, `position` (keeps order), `dims`, `units`, `label`, `metadata`, `values_hash`, `uncertainty_hash` |
| `blobs` | distinct array content | `hash` (sha256 of dtype+shape+bytes), `dtype`, `shape`, `codec`, `nbytes`, `data` (BLOB) |
| `annotations` | Annotation | `kind`, `name`, `data` (JSON object), `metadata` |
| `dataset_parents` | lineage edge | `child_id` -> `parent_id`; parent has **no** foreign key on purpose (a record of origin survives deleting the parent) |

**dtypes:** `bool`, `uint8`, `int16`, `uint16`, `int32`, `int64`, `float32`, `float64`, `complex128`, and `json` (fallback).
Inferred automatically. Anything that is not a rectangular block of numbers -- strings, `None`, ragged lists, dicts, huge ints -- is stored
as JSON, so **nothing a tool returns is unstorable**.

**Round-trip rules** (tested): tuples come back as lists; dict keys come back as strings; an int/float mix comes back all float;
`NaN`/`inf`/`-0.0` are exact.

**Guarantees:** atomic per dataset (or per `save_all`); every array is checksum-verified on load; identical arrays are stored once;
opening a file from a newer mtools or a foreign SQLite file is refused, never modified; older files are upgraded automatically after
a backup copy (`file.mtools.bak-v<old>`); thread-safe (worker threads may save).

**Limits:** one array must stay below ~0.9 GB stored (SQLite's per-value limit) -- you get a clear error telling you to downsample or split.
Loading decodes into Python lists (no numpy), so RAM, not disk, is the practical ceiling for very large PDE stacks. `load_dataset(id, arrays=[...])`
reads only the arrays you name.

## 4. Using it

```python
from data import store
from data.dataset import DataSet, DataArray, Annotation
from data.project import Project

# --- as a tool author: build a derived result ---------------------------------------
src = store.get()
out = src.derive("Output of Grain Analysis", "Grain Analysis", {"threshold_nm": 1.5})   # new id, parents=[src.id], params recorded
out.add(DataArray(values=0.83, name="Ra", units="nm", uncertainty=0.02))
out.annotations.append(Annotation("grain", {"area": 4.5, "centroid": [1.2, 3.4]}, name="Grain 1"))
store.add(out)                       # in memory -- and in the project file if one is attached

# --- as an app author: project files -------------------------------------------------
store.open_project("afm_run_3.mtools")      # or store.open_autosave()
store.save_project_as("backup.mtools")

# --- browsing without loading data ---------------------------------------------------
with Project.open("afm_run_3.mtools", readonly=True) as p:
    for info in p.list_datasets(source_tool="Grain Analysis"):
        print(info.name, [(a.name, a.shape, a.dtype) for a in info.arrays])
    p.ancestors(out.id)                                              # the computation chain
    p.sql("SELECT json_extract(data,'$.area') AS a FROM annotations WHERE kind='grain'")   # read-only SQL

# --- sharing -------------------------------------------------------------------------
from data import interchange
interchange.export_json("result.json", out)      # loaders.load_dataset("result.json") reads it back
```

`ComputeToolWindow` already does the provenance for you: **"Send result to workspace"** builds the dataset through
`DataSet.from_result(...)` with `source_tool`, `parents=[the input dataset]` and `params=self.get_params()`.
Override `get_params()` in a tool to record its inputs (degree, formula, seed ...).

## 5. Rules for tool authors

1. **Never mutate the dataset you were given.** `derive()` (or `copy()`) it -- a chain of results stays trustworthy, and lineage is recorded for free.
2. **Put every input that affects the result into `params`** (method, tolerances, formula, initial guess ...). **Simulations: always store the `seed`.**
3. **Don't copy inputs "for safety" into the result -- reference them via `parents`.** If you do carry an array along unchanged it costs no disk space (content-addressed).
4. **Coordinates go in `axes`** (1-D `DataArray`, name = dimension name, e.g. `x`, `t`, `freq`). Values in `data` name their axes in `dims`, e.g. `dims=("y","x")`.
   `DataSet.validate()` catches wrong ranks and lengths; `store`/`Project` log the problems (use `strict=True` in tests).
5. **Masks and labels are ordinary data arrays** (`bool` / int) with the same `dims` as the array they belong to and `metadata={"mask_for": "height"}`.
6. **Uncertainty** = `DataArray.uncertainty`, same shape as `values` (or a scalar for a scalar).
7. **Many small records** (peaks, grains, optimizer steps) -> `Annotation(kind, data={...})`. **Big numeric series** -> arrays.
8. **Complex is fine** -- store the complex array; don't split into re/im unless the tool wants both.
9. **Units are plain strings** (`"nm"`, `"1/cm"`). Custom unit *definitions* live in `settings.custom_units()`.
10. Scalars are just 0-d values: `DataArray(values=0.83, name="Ra")`.

## 6. Recipe per tool category

`tests/test_tool_recipes.py` builds exactly these, saves them to a real file and to JSON, and checks they come back unchanged.

| Category | axes | data | annotations | `params` (examples) |
|---|---|---|---|---|
| **fitting** | `x` (,`y`,`z`) of the points | coefficients as scalars (with `uncertainty` = std error), `y_fit`, `residual`, `r2`, `ssr` | -- | `degree`, `formula`, `param_names`, `p0`, `iterations` |
| **afm** | `x`,`y` (um) | `height` (`dims=("y","x")`, nm), `phase`..., `defect_mask` (bool), `grain_labels` (int), `Ra`, `Rq` | `grain` {area, perimeter, centroid, ...} | `level`, `rotate_deg`, `crop`, `threshold_nm`; scan size / instrument / source format in `metadata` |
| **ode** | `t` | `y` (`dims=("t","state")`), `success` | -- | `rhs`, `y0`, `method`, `rtol`, `atol` |
| **pde** | `t`,`y`,`x` | `u` (`dims=("t","y","x")`) | -- | `equation`, `scheme`, `dt`, `dx`, `boundary`, `initial` |
| **statistics** | index / value axis | descriptive: one scalar per statistic; tests: `statistic`, `p_value`, `decision`; preprocessing: cleaned arrays + bool `removed`; `NaN` = missing value | -- | `test`, `alpha`, `alternative`, `level`, `outliers` |
| **spectroscopy** | `wavelength` / `wavenumber` | `intensity`, `baseline`, `fit` | `peak` {center, width, amplitude, area, model} | `model`, `window` |
| **simulation** | `depth`,`time`,... | `samples`, `bin_edges`, `counts`, distributions | -- | **`seed`**, `n_runs`, `model`; ragged trajectories -> pad + `lengths` array |
| **transformation** | `t` -> `freq` | complex `spectrum`; `F(sigma, omega)` for Laplace | -- | `window`, `normalize`, `sigma` |
| **optics** | `x`,`y` (m) | complex `field`, real `intensity` | -- | `wavelength_m`, `slit_width_m`, `distance_m` |
| **units** | -- | converted array with new `units` | -- | `from`, `to`, `factor`; definitions in `settings` |
| **linear_algebra** | -- | `A`, `L`,`U`,`P` / `Q`,`R` / `U`,`S`,`Vt`, complex `eigenvalues`/`eigenvectors`, `x`, `residual` | -- | `method`, `pivoting`; condition number in `metadata` |
| **interpolation** | `knots`, `x_eval` | `coefficients` (`dims=("piece","power")`), `y_eval` | -- | `kind`, `boundary` |
| **optimization** | -- | `x_opt` (+uncertainty), `f_opt`, `converged`, `x_history` (`("iter","dim")`), `f_history` | `step` {iter, x, f, grad_norm} for short runs, `root` | `method`, `x0`, `tol`, `bounds` |
| **error_propagation** | -- | `result` with `uncertainty`, `covariance` | -- | `expression`, `variables`, `method`; the chain = `parents` -> `project.ancestors(id)` |

## 7. Changing the schema later

Add `MIGRATIONS[n]` in `data/schema.py` (SQL that upgrades from `n-1`), bump `SCHEMA_VERSION`, add a test (see
`tests/test_project.py::Migrations`). Existing files upgrade themselves on open, after a backup copy, in one transaction.

## 8. Settings file

`%APPDATA%\mtools\settings.json` (Windows), `~/Library/Application Support/mtools/` (macOS), `~/.config/mtools/` (Linux); override with
`MTOOLS_HOME`. Broken files are moved aside (`settings.json.corrupt-<time>`) and defaults are used -- the app always starts.
Per-tool memory uses the tool's module name as key: `settings().save_preset("tools.fitting.regression.custom_nonlinear", "Decay", {...})`.
Custom units: `settings().set_custom_unit("angstrom", "Angstrom", [1,0,0,0,0,0,0], 1e-10)` (dims = exponents of L, M, T, I, Theta, N, J; `offset` for degC-like scales).
