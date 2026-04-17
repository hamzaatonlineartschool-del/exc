#!/usr/bin/env python3
"""Merge Udemy topic CSV exports into taxonomy_data.ENTRIES (dedupe topics, keep order)."""

from __future__ import annotations

import csv
import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from taxonomy_data import ENTRIES  # noqa: E402

TARGET_MAINS = frozenset(
    {
        "Health & Fitness",
        "Teaching & Academics",
        "Photography & Video",
        "Music",
    }
)

# Map Udemy subcategory labels -> our taxonomy subcategory names
SUB_ALIASES: dict[str, dict[str, str]] = {
    "Health & Fitness": {
        "General": "General Health",
        "Nutrition Diet": "Nutrition & Diet",
    },
    "Photography & Video": {
        "Other Photography": "Other Photography & Video",
    },
}

# Normalize obvious CSV typos / casing when adding a topic
TOPIC_FIXES = {
    "wolrd history": "World History",
    "teachiing online": "Teaching Online",
    "logic pro": "Logic Pro",
}


def norm_topic(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    key = s.lower()
    return TOPIC_FIXES.get(key, s)


def add_unique(lst: list[str], topic: str) -> None:
    topic = norm_topic(topic)
    if not topic:
        return
    seen = {x.casefold() for x in lst}
    if topic.casefold() not in seen:
        lst.append(topic)


def load_health(path: Path, merge: dict[tuple[str, str], list[str]]) -> None:
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            main = (row.get("Main") or "").strip()
            sub = (row.get("Sub category") or row.get("Subcategory") or "").strip()
            topic = (row.get("Topic Name") or row.get("Topic") or "").strip()
            if main not in TARGET_MAINS:
                continue
            sub = SUB_ALIASES.get(main, {}).get(sub, sub)
            key = (main, sub)
            merge.setdefault(key, [])
            add_unique(merge[key], topic)


def load_teaching(path: Path, merge: dict[tuple[str, str], list[str]]) -> None:
    """CSV columns: Main, Topic (= subcategory), Subcategory (= nested topic)."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            main = (row.get("Main") or "").strip()
            sub = (row.get("Topic") or "").strip()
            topic = (row.get("Subcategory") or "").strip()
            if main not in TARGET_MAINS:
                continue
            sub = SUB_ALIASES.get(main, {}).get(sub, sub)
            key = (main, sub)
            merge.setdefault(key, [])
            add_unique(merge[key], topic)


def load_simple(path: Path, merge: dict[tuple[str, str], list[str]], topic_col: str) -> None:
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            main = (row.get("Main") or "").strip()
            sub = (row.get("Subcategory") or "").strip()
            topic = (row.get(topic_col) or "").strip()
            if main not in TARGET_MAINS:
                continue
            sub = SUB_ALIASES.get(main, {}).get(sub, sub)
            key = (main, sub)
            merge.setdefault(key, [])
            add_unique(merge[key], topic)


def build_merged() -> dict[tuple[str, str], list[str]]:
    # Start from current taxonomy (preserve each topic list)
    om: dict[tuple[str, str], list[str]] = {}
    for m, s, topics in ENTRIES:
        om[(m, s)] = list(topics)

    udemy: dict[tuple[str, str], list[str]] = {}
    downloads = Path.home() / "Downloads"

    files = [
        (downloads / "Udemy_Health_Fitness_Course_Counts.csv", "health"),
        (downloads / "Udemy_Teaching_Academics_rse_Counts copy.csv", "teaching"),
        (downloads / "Udemy_Photography_Video_Course_Counts.csv", "photo"),
        (downloads / "Udemy_Music_Course_Counts.csv", "music"),
    ]

    for path, kind in files:
        if not path.is_file():
            print(f"skip missing: {path}", file=sys.stderr)
            continue
        if kind == "health":
            load_health(path, udemy)
        elif kind == "teaching":
            load_teaching(path, udemy)
        elif kind == "photo":
            load_simple(path, udemy, "Topic Name")
        elif kind == "music":
            load_simple(path, udemy, "Topic")

    # Merge Udemy into om for keys that exist OR are new under TARGET_MAINS
    for key, new_topics in udemy.items():
        main, _ = key
        if main not in TARGET_MAINS:
            continue
        if key not in om:
            om[key] = []
        for t in new_topics:
            add_unique(om[key], t)

    return om


def _baseline_keys() -> list[tuple[str, str]]:
    path = ROOT / "scripts" / "udemy_merge_baseline_order.txt"
    if not path.is_file():
        return list(OrderedDict.fromkeys((m, s) for m, s, _ in ENTRIES))
    keys: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        main, _, rest = line.partition("\t")
        keys.append((main, rest))
    return keys


def ordered_entries(om: dict[tuple[str, str], list[str]]) -> list[tuple[str, str, list[str]]]:
    baseline_keys = _baseline_keys()
    orig_set = set(baseline_keys)

    last_idx: dict[str, int] = {}
    for i, (m, _) in enumerate(baseline_keys):
        last_idx[m] = i

    new_by_main: dict[str, list[tuple[str, str]]] = {}
    for main in TARGET_MAINS:
        nk = sorted(
            (k for k in om if k[0] == main and k not in orig_set),
            key=lambda x: x[1].casefold(),
        )
        if nk:
            new_by_main[main] = nk

    out: list[tuple[str, str, list[str]]] = []
    for i, k in enumerate(baseline_keys):
        m, s = k
        topics = om[k]
        out.append((m, s, topics))
        if last_idx.get(m) == i and m in new_by_main:
            for nk in new_by_main[m]:
                out.append((nk[0], nk[1], om[nk]))
    return out


def write_taxonomy_py(path: Path, entries: list[tuple[str, str, list[str]]]) -> None:
    lines = [
        '"""Course taxonomy: (main_category, subcategory, list of nested topics in order)."""',
        "",
        "# Topic lists vary in length; merged from Udemy exports + manual curation.",
        "ENTRIES: list[tuple[str, str, list[str]]] = [",
    ]
    for main, sub, topics in entries:
        lines.append(f"    ({main!r}, {sub!r}, {topics!r}),")
    lines.append("]")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    om = build_merged()
    entries = ordered_entries(om)
    out = ROOT / "taxonomy_data.py"
    write_taxonomy_py(out, entries)
    n = sum(len(t) for _, _, t in entries)
    print(f"Wrote {out} — {len(entries)} subcategories, {n} topic rows")


if __name__ == "__main__":
    main()
