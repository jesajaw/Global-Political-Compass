

---

## Project structure

The app is written in tkinter (standard library only) and has three areas:

| Area | Folder | What it does |
|------|--------|--------------|
| **UI**    | `ui/`    | The windows: the compass (`compass_window/`) and the data window (`data_window/`), styled like mtools (`style.py`, `dialogs.py`, `widgets.py`). |
| **AGENT** | `agent/` | Asks a local LLM via Ollama to rate a country for a year (`python -m agent.setup_model` installs the model). |
| **DATA**  | `data/`  | `countries.json` (the country list), one JSON file per country in `data/countries/` (created when its first entry is added), and `scoring.py` for evaluation. |

**How scores work:** every country can hold any number of entries per year (added by hand or by the agent).
`data.scoring.get_score(country_id, year)` returns the average of all entries of that year -- that average is what the compass plots.
There is no demo data: an empty compass simply means nothing has been entered yet.

**Categories (`data/categories.py`):** an entry can additionally carry a breakdown across 10 categories
(Economy, Taxation, Social Policy, State Ownership, Migration, Civil Liberties, Law & Order,
Nationalism/Internationalism, Environment, Foreign Policy), each rated -10..+10. Six of them feed
one of the two plotted axes (their mean, *10); Environment and Foreign Policy are context-only --
visible on hover, never plotted. See `data.categories.axes_from_categories` for the mapping and
`data.scoring.get_category_breakdown` for reading it back. A plain manual entry can skip categories
entirely and set Left/Right and Lib/Auth directly; both forms are equally valid.

**Origin:** every entry is `"manual"` (typed in by hand), `"ai"` (written by the agent, unreviewed) or
`"manual_ai"` (an agent entry a person has since edited -- store.py promotes it automatically the
moment it's saved through the form again). The Data window's tree and edit form both show this,
plus which model produced it.

**Agent model choice:** `llama3.3:70b` is the default -- see the docstring of `agent/llm_client.py`
for why (comparatively less lab-shifted among locally runnable models, per one third-party
benchmark) and its limits (it is not neutral, just less shifted; re-evaluate before relying on it).

**Agent backend -- local vs. hosted:** `llama3.3:70b` needs roughly 40+ GB RAM/VRAM even
quantized, which most laptops and single consumer GPUs don't have. `agent/llm_client.py` supports
two backends, switched with one environment variable, no code change:

| | `AGENT_BACKEND=ollama` (default) | `AGENT_BACKEND=api` |
|---|---|---|
| Runs | locally via [Ollama](https://ollama.com) | any OpenAI-compatible hosted API (OpenAI, xAI/Grok, Groq Cloud, Together, Fireworks, OpenRouter, ...) |
| Needs | ~40+ GB RAM/VRAM for the 70B model, or a smaller `AGENT_MODEL` | an API key and per-token cost, no local hardware |
| Install | `python -m agent.setup_model` (pulls the model) | nothing to install |
| Config | `AGENT_MODEL` (+ `OLLAMA_URL` if not default) | `AGENT_API_BASE_URL`, `AGENT_API_KEY`, `AGENT_MODEL` |

Copy `agent/set_backend.example.ps1` to `agent/set_backend.ps1` (already git-ignored, since that's
where a real API key would live), uncomment the option you want, and dot-source it
(`. .\agent\set_backend.ps1`) before running the app. Since each country/year is now one model
call (all 10 categories in one prompt, see `agent/evaluate.py`), the hosted option is cheap even
across many countries.

**Evidence quality -- sources, verification, red-team review:** a model can invent plausible-looking
URLs, so "the agent cited a source" isn't the same as "the source is real". Two features address
this, both opt-in (they cost extra calls/time), both available from the CLI and the Data window:

- **Source verification** (`agent/verify.py`, `--verify-sources` / the "Verify sources" checkbox):
  each cited URL is actually fetched; the result (`entry.sources_verified: {url: bool}`) is stored
  and shown in the tooltip and the Data window ("Sources: 2/3 reachable"). A `False` means it didn't
  answer just now, not proof the source is fake.
- **Red-team review** (`agent/review.py`, `--review` / the "Red-team review" checkbox): a SECOND
  model critiques the first model's ratings and evidence. It can only lower a category's
  `confidence` (never touch the score, never raise confidence) and leaves a note
  (`entry.review_notes`, `entry.reviewed_by`), shown the same places. Configure the reviewer via
  `AGENT_REVIEW_MODEL` / `AGENT_REVIEW_BACKEND` (+ `AGENT_REVIEW_API_*` if it's a different hosted
  provider) -- see `agent/review.py`'s docstring. Reviewing with the same model as the main one is
  allowed but weaker: shared training data means shared blind spots, so this only really earns its
  name with a genuinely different model.

**Calibration (`data/calibrate.py`):** measures the agent's systematic offset against a handful of
reference countries whose position you trust from an independent source, e.g.:

    python -m data.calibrate --reference data/reference_countries.example.json --year 2024

Copy that example file first and replace its placeholder `"source"` fields with something real --
it ships with illustrative numbers only, clearly marked, not a trustworthy dataset. The script only
prints a suggested `CORRECTION_LR` / `CORRECTION_LA` for `data/categories.py`; it never edits that
file itself, so a correction only takes effect once you've looked at the numbers and set them
yourself.

**Export (`data/export.py`):** every stored entry, or the averaged per-country scores, as CSV --
for a spreadsheet, R, pandas, whatever. Command-line only (no button in the Data window, to keep
it uncluttered): `python -m data.export --help` for the options (`--year`, `--scores`, `--out`).

**Tests (`tests/`):** a shipped, dependency-free test suite -- run `python -m tests.run_all` after
changing anything to check the data layer, the category math, both agent parsing paths, both
LLM backends, verify/review, export/calibration and the full UI flow still work. Nothing in it
touches a real network, model, or your actual `data/countries/`. See `tests/README.md`.

Run with `python main.py` (compass) or `python data_editor.py` (data window only).
Batch-rate many countries: `agent\batch.ps1 -Year 2025 -ListFile agent\countries.example.txt -SkipExisting` (PowerShell).
