# 🌐 Global Political Compass AI Engine

> ⚠️ **Status: Under Development**  
> This is a prototype for the AI-assisted evaluation of countries on the 2D political compass (Left/Right & Libertarian/Authoritarian).

So what is this about? Global politics are in my eyes really overwhelming and so polarised that you often can't really see what is actually happening or compare with other countries also because there is so much happening -- which does not have to be bad at all -- but may sometimes be a bit much.

That's how this project-idea came together: nowadays you will find almost everything on the internet and as long as you don't use AI-Slop or some weird sources, you can actually evaluate the whole political direction of every country. So I tried to find a way of analyzing different sides, publications and political statements / texts in a hopefully kind of objective way (which is obviously not the exact case; see [Disclaimer](#-disclaimer)) to compare the global political situation.

## Disclaimer

As remarked -- it is not possible to work totally objective and I do not want to state it here — there are and there will be misevaluations, bugs and obviously a slight opinion of my own! I am the only contributor, most likely this will no one read or use except of me, so there is also no other independent verification or fundamental criticism. So use and think of it without any warranty -- it's not possible to evaluate politics like this totally objective -- also due to these short time intervals between the event and the evaluation.

---

## 📌 Overview

This tool (is intended to eventually) analyze the political and economic systems of countries using large language models (OpenAI GPT-4o) and store structured profile data in JSON format.

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

Run with `python main.py` (compass) or `python data_editor.py` (data window only).