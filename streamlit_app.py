"""Course taxonomy dashboard for Streamlit Cloud."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"


@st.cache_data
def load_manifest() -> dict:
    p = PUBLIC / "manifest.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


@st.cache_data
def load_taxonomy() -> list[dict]:
    p = PUBLIC / "taxonomy.json"
    if not p.is_file():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    st.set_page_config(
        page_title="Course taxonomy",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    with st.sidebar:
        st.header("Update pipeline")
        st.markdown(
            """
1. Edit **`taxonomy_data.py`** or merge Udemy CSVs:
   ```bash
   python scripts/merge_udemy_taxonomy.py
   ```
2. Rebuild workbook + `public/`:
   ```bash
   python scripts/build_taxonomy_workbook.py
   ```
3. Commit **`public/`** (and `dist/` if tracked) and push — Streamlit redeploys from the repo.
            """
        )
        if st.button("Clear cached data"):
            st.cache_data.clear()
            st.rerun()

    st.title("Course taxonomy dashboard")
    st.caption(
        "Topics load from **`public/taxonomy.json`** and **`public/manifest.json`** in this repository "
        "(variable-length topic lists per subcategory after Udemy merges)."
    )

    manifest = load_manifest()
    rows = load_taxonomy()

    if not manifest or not rows:
        st.error(
            "Missing `public/manifest.json` or `public/taxonomy.json`. "
            "Run `python scripts/build_taxonomy_workbook.py`, commit `public/`, and redeploy."
        )
        st.stop()

    unique_mains = len({r["main_category"] for r in rows})
    unique_sub_pairs = len({(r["main_category"], r["subcategory"]) for r in rows})
    unique_nested_names = len({r["nested_category"] for r in rows})
    total_courses = len(rows)

    with st.expander("How counts work", expanded=False):
        st.markdown(
            """
- **Main categories** — distinct top-level names.
- **Unique subcategories** — distinct *(main, subcategory)* pairs (no double-counting the same pair).
- **Nested topics (unique names)** — distinct nested topic titles **globally** (e.g. “Python” counted once).
- **Total courses** — one row per topic placement; the same title under different paths counts again.

Manifest fields `total_courses` / `unique_nested_topic_labels` should match the table above after a fresh build.
            """
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Main categories", f"{unique_mains:,}")
    c2.metric("Unique subcategories", f"{unique_sub_pairs:,}")
    c3.metric("Nested topics (unique names)", f"{unique_nested_names:,}")
    c4.metric("Total courses", f"{total_courses:,}")

    m_tc = manifest.get("total_courses")
    m_un = manifest.get("unique_nested_topic_labels")
    if m_tc is not None and m_un is not None and (m_tc != total_courses or m_un != unique_nested_names):
        st.warning(
            f"Manifest totals differ from loaded JSON (manifest: courses={m_tc}, unique nested={m_un}). "
            "Rebuild and redeploy so `public/` matches."
        )

    dl1, dl2, dl3 = st.columns(3)
    xlsx_path = PUBLIC / "Course_Taxonomy_Master.xlsx"
    csv_path = PUBLIC / "taxonomy.csv"
    json_path = PUBLIC / "taxonomy.json"

    st.subheader("Downloads")
    if xlsx_path.is_file():
        dl1.download_button(
            "Excel (.xlsx)",
            data=xlsx_path.read_bytes(),
            file_name="Course_Taxonomy_Master.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    if csv_path.is_file():
        dl2.download_button(
            "CSV",
            data=csv_path.read_bytes(),
            file_name="taxonomy.csv",
            mime="text/csv",
            use_container_width=True,
        )
    if json_path.is_file():
        dl3.download_button(
            "JSON",
            data=json_path.read_bytes(),
            file_name="taxonomy.json",
            mime="application/json",
            use_container_width=True,
        )

    st.subheader("Rows per main category")
    counts = manifest.get("main_category_row_counts") or {}
    ordered = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
    st.bar_chart(pd.Series(ordered, name="Rows", dtype="int"))

    st.subheader("Browse topics")
    mains = sorted({r["main_category"] for r in rows})
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        main_filter = st.selectbox("Main category", options=["(All)"] + mains, index=0)
    subs = sorted(
        {
            r["subcategory"]
            for r in rows
            if main_filter == "(All)" or r["main_category"] == main_filter
        }
    )
    with col_b:
        sub_filter = st.selectbox("Subcategory", options=["(All)"] + subs, index=0)
    with col_c:
        q = st.text_input("Search nested topic", placeholder="Substring match…", value="")

    def keep(r: dict) -> bool:
        if main_filter != "(All)" and r["main_category"] != main_filter:
            return False
        if sub_filter != "(All)" and r["subcategory"] != sub_filter:
            return False
        if q.strip() and q.strip().lower() not in r["nested_category"].lower():
            return False
        return True

    filtered = [r for r in rows if keep(r)]
    st.caption(
        f"Showing **{len(filtered):,}** of **{len(rows):,}** rows · "
        f"Built (UTC): `{manifest.get('built_at', '—')}`"
    )

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        height=min(520, 36 + len(filtered) * 35),
        column_config={
            "rank": st.column_config.NumberColumn("Rank", format="%d"),
            "main_category": "Main category",
            "subcategory": "Subcategory",
            "nested_category": "Nested category",
        },
    )


if __name__ == "__main__":
    main()
