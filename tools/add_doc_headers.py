#!/usr/bin/env python3
"""One-off: add the five line header to every markdown doc that lacks one.

Title comes from the file's own first heading, date from the filename when it carries one
(falling back to the last git commit date, then to the file mtime), type from the folder.
Existing content is never touched, only prefixed. Run once, then use tools/index_docs.py.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from index_docs import SKIP_DIRS, derive_type, filename_date  # noqa: E402

SKIP = {"docs/INDEX.md", "notiondocs.md", "AGENTS.md"}


def git_date(rel):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%ad", "--date=short", "--", rel],
                             cwd=ROOT, capture_output=True, text=True, timeout=20)
        return out.stdout.strip() or None
    except Exception:
        return None


def first_heading(text):
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return ""


def title_from_name(name):
    return name[:-3].replace("_", " ").replace("-", " ").strip().capitalize()


def build_header(rel, text, full):
    title = first_heading(text) or title_from_name(os.path.basename(rel))
    title = title.replace("—", "-").replace("–", "-")
    date = filename_date(os.path.basename(rel)) or git_date(rel) or \
        __import__("datetime").date.fromtimestamp(os.path.getmtime(full)).isoformat()
    typ = derive_type(rel)
    status = "done" if ("archive" in rel.replace("\\", "/")) else "active"
    return (f"---\ntitle: {title}\ndate: {date}\ntype: {typ}\nstatus: {status}\nwhere: {rel}\n---\n\n")


def main():
    changed, skipped = [], []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            if rel in SKIP:
                skipped.append(rel)
                continue
            raw = open(full, encoding="utf-8", errors="replace").read()
            if raw.lstrip().startswith("---"):
                skipped.append(rel)
                continue
            crlf = "\r\n" in raw
            header = build_header(rel, raw, full)
            if crlf:
                header = header.replace("\n", "\r\n")
            with open(full, "w", encoding="utf-8", newline="") as f:
                f.write(header + raw)
            changed.append(rel)
    for r in sorted(changed):
        print("  header added:", r)
    print(f"\nadded: {len(changed)}   already had a header: {len(skipped)}")


if __name__ == "__main__":
    main()
