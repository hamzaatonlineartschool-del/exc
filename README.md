# Course taxonomy workbook

Single Excel file with a **Master** sheet (all topics) and **one sheet per main category**. Columns everywhere:

| Main Category | Subcategory | Nested category | Rank |

- **Source of truth:** [`taxonomy_data.py`](taxonomy_data.py) (`ENTRIES` — each subcategory has nine nested topics).
- **Personal Development:** the **Motivation** subcategory replaces the old *Personal Transformation* list from the original brief.

## Build locally

```bash
python3 -m venv .venv && source .venv/bin/activate  # optional
pip install -r requirements.txt
python scripts/build_taxonomy_workbook.py
```

Outputs:

- `dist/Course_Taxonomy_Master.xlsx` — workbook with Excel **Tables** and filters on each sheet.
- `dist/manifest.json` — build time, row counts by main category.
- `dist/taxonomy.csv` — flat export of the same rows.
- `dist/taxonomy.json` — same rows as JSON (used by the web dashboard).

The script copies **workbook**, **manifest.json**, **taxonomy.json**, and **taxonomy.csv** into [`public/`](public/) for hosting.

## Web dashboard

[`public/index.html`](public/index.html) is a static **dashboard**: build stats, horizontal bar chart by main category, **filters** (main category, subcategory, search on nested topic), a **scrollable topic table**, and download buttons for Excel, CSV, and JSON.

Serve the `public/` folder over HTTP (browsers block `fetch` from `file://`):

```bash
python3 -m http.server 8765 --directory public
```

Then open `http://localhost:8765/`.

Enable **GitHub Pages** with source **/public** on your default branch if you want a public URL; rebuild and push (or extend CI) so `taxonomy.json` stays in sync with the workbook.

### Streamlit Community Cloud

Use **[`streamlit_app.py`](streamlit_app.py)** as the entry file. Settings:

| Field | Value |
|-------|--------|
| **Repository** | `hamzaatonlineartschool-del/exc` (repo you pushed — not `exce` unless that repo exists and has this code) |
| **Branch** | `main` (this project does not use `master`) |
| **Main file path** | `streamlit_app.py` |

The app reads **`public/manifest.json`**, **`public/taxonomy.json`**, and download binaries from **`public/`**. After taxonomy changes, run the build script, commit `public/` (and `dist/` if you track it), then redeploy.

## CI

GitHub Actions workflow [`.github/workflows/build-taxonomy.yml`](.github/workflows/build-taxonomy.yml) builds on push and uploads **course-taxonomy** artifacts (xlsx, manifest, csv, json).

## Editing taxonomy

Edit tuples in `taxonomy_data.py`, re-run the build script, commit `dist/` and `public/` if you want them versioned, or rely on CI artifacts only.
