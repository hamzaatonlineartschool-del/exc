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


def main():
    st.set_page_config(page_title="Course taxonomy", layout="wide")
    st.title("Course taxonomy dashboard")
    st.caption("Data comes from `public/` in this repo. Re-run `python scripts/build_taxonomy_workbook.py` after editing `taxonomy_data.py`, then commit and push.")

    manifest = load_manifest()
    rows = load_taxonomy()

    if not manifest or not rows:
        st.error(
            "Missing `public/manifest.json` or `public/taxonomy.json`. "
            "Run the build script locally, commit outputs, and push."
        )
        st.stop()

    c1, c2, c3 = st.columns(3)
    c1.metric("Topic rows", f"{manifest.get('row_count', 0):,}")
    c2.metric("Main categories", manifest.get("main_category_count", "—"))
    c3.metric("Subcategories", manifest.get("subcategory_count", "—"))

    st.subheader("Downloads")
    xlsx_path = PUBLIC / "Course_Taxonomy_Master.xlsx"
    if xlsx_path.is_file():
        st.download_button(
            "Download Excel (.xlsx)",
            data=xlsx_path.read_bytes(),
            file_name="Course_Taxonomy_Master.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    csv_path = PUBLIC / "taxonomy.csv"
    if csv_path.is_file():
        st.download_button(
            "Download CSV",
            data=csv_path.read_bytes(),
            file_name="taxonomy.csv",
            mime="text/csv",
        )
    json_path = PUBLIC / "taxonomy.json"
    if json_path.is_file():
        st.download_button(
            "Download JSON",
            data=json_path.read_bytes(),
            file_name="taxonomy.json",
            mime="application/json",
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
    st.caption(f"Showing **{len(filtered):,}** of **{len(rows):,}** rows · Built (UTC): `{manifest.get('built_at', '—')}`")

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "rank": st.column_config.NumberColumn("Rank", format="%d"),
            "main_category": "Main category",
            "subcategory": "Subcategory",
            "nested_category": "Nested category",
        },
    )


if __name__ == "__main__":
    main()
