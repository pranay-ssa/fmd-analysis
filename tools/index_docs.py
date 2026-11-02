#!/usr/bin/env python3
"""Generate docs/INDEX.md: the route through this repository.

Every markdown file may carry a five line header:

    ---
    title: Crop margin sweep
    date: 2026-09-19
    type: result          # result | decision | protocol | method | session | report | doc | experiment | state
    status: active        # active | done | superseded
    where: reports/preprocessing/crop_margin.md
    ---

Files without a header still appear: the date is read from the filename when it looks like
`something_20260919.md`, and the type is derived from the folder. So the index is useful from
the first run and gets better as headers are added. Nothing here is hand maintained.

Run:  python tools/index_docs.py [--check]

--check exits non-zero if any file is missing a header, for use before a commit.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "INDEX.md")

SKIP_DIRS = {".git", ".venv", "run", "model_runs", ".obsidian", ".obsidian-vault",
             "__pycache__", "node_modules", "data", "vm", "tests", "src", "notebooks",
             # Scratch and machine-generated trees: git worktree copies of this repo (.delta)
             # and the rewritten-on-every-build knowledge graph output. Both duplicate or
             # regenerate real documents, so indexing them double-counts the repo.
             ".delta", "graphify-out"}

# folder -> type, used when a file has no header
TYPE_BY_DIR = [
    ("docs/protocol", "protocol"),
    ("docs/method", "method"),
    ("docs/decisions", "decision"),
    ("docs/sessions", "session"),
    ("docs/reference", "reference"),
    ("docs/archive", "archive"),
    ("docs/transfer", "transfer"),
    ("reports", "report"),
    ("experiments", "experiment"),
    ("docs", "doc"),
]

ORDER = ["state", "session", "result", "decision", "report", "experiment",
         "protocol", "method", "reference", "doc", "transfer", "task", "archive", "other"]

# root level files carry their own meaning
ROOT_TYPES = {"HANDOFF.md": "state", "README.md": "reference", "AGENTS.md": "reference"}


def parse_header(text: str) -> dict:
    """Read a leading --- block of `key: value` lines. No YAML dependency, on purpose."""
    if not text.startswith("---"):
        return {}
    out = {}
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.split("#", 1)[0].strip()
            out[k.strip().lower()] = v
    return out


def first_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def filename_date(name: str):
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", name)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            return None
    return None


def derive_type(rel: str) -> str:
    p = rel.replace("\\", "/")
    if "/" not in p and p in ROOT_TYPES:
        return ROOT_TYPES[p]
    for prefix, t in TYPE_BY_DIR:
        if p.startswith(prefix):
            return t
    return "other"


def collect():
    rows = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            # Generated, never hand-edited: the index itself, the local staging file, and the
            # knowledge graph report (rewritten whole on every graphify build, so a header
            # there would vanish on the next run).
            if rel in ("docs/INDEX.md", "notiondocs.md") or rel.startswith("graphify-out/"):
                continue
            try:
                text = open(full, encoding="utf-8", errors="replace").read(4000)
            except OSError:
                continue
            h = parse_header(text)
            rows.append({
                "path": rel,
                "header": bool(h),
                "title": h.get("title") or first_heading(text) or fn[:-3],
                "date": h.get("date") or filename_date(fn) or "",
                "type": h.get("type") or derive_type(rel),
                "status": h.get("status") or ("done" if "archive" in rel else "active"),
                # Kept separate from "status": filters must match only what the header
                # actually says, never the derived fallback (see --skip-status).
                "explicit_status": h.get("status") or "",
                "where": h.get("where") or "",
                "size": os.path.getsize(full),
            })
    return rows


def build(rows):
    today = dt.date.today().isoformat()
    by_type = {}
    for r in rows:
        by_type.setdefault(r["type"], []).append(r)
    for v in by_type.values():
        v.sort(key=lambda r: (r["date"] or "0000-00-00", r["path"]), reverse=True)

    lines = [
        "---",
        "title: Route through this repository",
        f"date: {today}",
        "type: reference",
        "status: active",
        "where: docs/INDEX.md",
        "---",
        "",
        "# Route",
        "",
        "Generated by `tools/index_docs.py`. Do not edit by hand: your edit is lost on the next run.",
        "A file appears here the moment it exists. Add the five line header to make its row precise.",
        "",
        f"Files indexed: {len(rows)}. Types: " + ", ".join(f"{t} ({len(v)})" for t, v in
            sorted(by_type.items(), key=lambda kv: ORDER.index(kv[0]) if kv[0] in ORDER else 99)) + ".",
        "",
    ]
    for t in ORDER:
        if t not in by_type:
            continue
        lines.append(f"## {t}")
        lines.append("")
        lines.append("| File | Date | Status | What it is |")
        lines.append("|---|---|---|---|")
        for r in by_type[t]:
            link = f"[{r['path']}](../{r['path']})"
            lines.append(f"| {link} | {r['date'] or 'undated'} | {r['status']} | {r['title']} |")
        lines.append("")

    missing = [r for r in rows if not r["header"]]
    lines += ["## Files still without a header", "",
              f"{len(missing)} of {len(rows)}. The index works without them (date from the filename, "
              "type from the folder), but a header is what makes a row precise. Add one when you next "
              "touch the file.", ""]
    for r in sorted(missing, key=lambda r: r["path"]):
        lines.append(f"- `{r['path']}`")
    lines.append("")
    return "\n".join(lines), len(missing)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if any file lacks a header")
    ap.add_argument("--skip-status", action="append", default=None, metavar="STATUS",
                    help="omit rows whose header status equals STATUS (repeatable, "
                         "comma-separated allowed). Defaults to 'superseded'.")
    ap.add_argument("--include-status", action="append", default=None, metavar="STATUS",
                    help="countermand --skip-status for STATUS (repeatable). Use "
                         "'--include-status superseded' to list archived decisions again.")
    args = ap.parse_args()

    rows = collect()

    # Superseded documents are skipped by default so a bare run cannot resurface them:
    # the whole point of this flag is that the route stops citing stale decisions, and
    # an opt-in filter would be undone by the next person who regenerates the index.
    skip = {"superseded"}
    for raw in (args.skip_status or []):
        skip.update(s.strip() for s in raw.split(",") if s.strip())
    for raw in (args.include_status or []):
        skip.difference_update(s.strip() for s in raw.split(",") if s.strip())
    if skip:
        # Status-keyed, not directory-keyed: superseded documents also live outside
        # docs/archive/ (docs/reference/, reports/), so a directory filter misses them.
        # Only an EXPLICIT header status is matched. A derived fallback would be wrong:
        # collect() derives 'done' for headerless archive paths, and 'done' on its own
        # means a finished ticket, not a superseded document -- filtering it would hide
        # finished wayfinder tickets that are still part of the route.
        kept, dropped = [], []
        for r in rows:
            explicit = r.get("explicit_status")
            (dropped if explicit in skip else kept).append(r)
        if dropped:
            print(f"skipped {len(dropped)} row(s) with status in {sorted(skip)}:")
            for r in sorted(dropped, key=lambda r: r["path"]):
                print(f"  {r['path']}")
        rows = kept

    text, missing = build(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(text)
    print(f"indexed {len(rows)} files, {missing} without a header")
    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    if args.check and missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
