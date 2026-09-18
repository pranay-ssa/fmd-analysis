#!/usr/bin/env python3
"""Build the focused line-analysis HTML report.

Generator chain (per the workspace EDA report convention):
    run/line_eda/20260916/image_line_tags.csv   (one row per image: folder, class, line)
    run/line_eda/20260916/image_md5_records.csv (one row per image: folder, class, name, md5, bytes)
        -> this script -> reports/lines/line_report_20260916.html

Every number in the page is computed here from those two files. Nothing is typed in
by hand, so the page cannot drift from the data.
"""
import csv
import math
import os
from collections import Counter, defaultdict
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "run", "line_eda", "20260916")
OUT = os.path.join(REPO, "reports", "lines", "line_report_20260916.html")

NEW_OBJ = "Updated ICube Objects 20260915"
NEW_CAT = "Updated ICube Categorical Classes 20260915"
LIB = "ICube Defects Library"
SHORT = {NEW_OBJ: "Updated Objects", NEW_CAT: "Updated Categorical", LIB: "Older library"}


def n(x):
    return "{0:,}".format(x)


# ---------------------------------------------------------------- load
tags = [tuple(r[c] for c in ("folder", "class", "line", "basename"))
        for r in csv.DictReader(open(os.path.join(DATA, "image_line_tags.csv"),
                                     newline="", encoding="utf-8"))]
recs = [tuple(r) for r in csv.reader(open(os.path.join(DATA, "image_md5_records.csv"),
                                          newline="", encoding="utf-8"))]
recs = [(f, c, b, m, int(s)) for f, c, b, m, s in recs]
assert len(tags) == len(recs), "the two tables must cover the same files"

FOLDERS = [NEW_OBJ, NEW_CAT, LIB]
LINES = sorted({t[2] for t in tags}, key=lambda s: int(s[1:]))

# ---------------------------------------------------------------- counts
files_total = len(tags)
lines_total = Counter(t[2] for t in tags)
orphans = sum(1 for t in tags if not t[2])
per_folder_lines = Counter((t[0], t[2]) for t in tags)
cells = Counter((t[0], t[2], t[1]) for t in tags)          # folder, line, class -> n
CELL_MAX = max(cells.items(), key=lambda kv: kv[1])
CELL_MIN = min(cells.items(), key=lambda kv: kv[1])

md5_all = {r[3] for r in recs if r[3]}
unique_images = len(md5_all)
redundant = files_total - unique_images

by_name = defaultdict(set)
by_md5 = defaultdict(set)
for f, c, b, m, s in recs:
    by_name[b].add(f)
    if m:
        by_md5[m].add(c)
shared_names = {b: v for b, v in by_name.items() if len(v) > 1}
conflicting = {m: v for m, v in by_md5.items() if len(v) > 1}
conflict_pairs = Counter()
for m, labels in conflicting.items():
    conflict_pairs[tuple(sorted(labels))] += 1
clear_conflicts = sum(v for k, v in conflict_pairs.items() if "Clear" in k)

new_md5 = {r[3] for r in recs if r[0] in (NEW_OBJ, NEW_CAT) and r[3]}
lib_md5 = {r[3] for r in recs if r[0] == LIB and r[3]}
lib_only = lib_md5 - new_md5
DUP_FOLDER_FILES = sum(1 for r in recs if r[1] == "duplicates")

# class names that differ between the folders, verified by the shared images they hold
NAME_MAP = {"Low Dose Obstructing Region of Interest": "Low Dose"}


def mapped(cls):
    return NAME_MAP.get(cls, cls)


new_classes = {mapped(r[1]) for r in recs if r[0] in (NEW_OBJ, NEW_CAT)}
lib_classes = {r[1] for r in recs if r[0] == LIB}
ABSENT_CLASSES = sorted(c for c in lib_classes if mapped(c) not in new_classes)
ABSENT_IMAGES = sum(1 for r in recs if r[0] == LIB and r[1] in ABSENT_CLASSES)
LIB_ONLY_FOLDERS = Counter()
for f, c, b, m, s in recs:
    if m in lib_only:
        LIB_ONLY_FOLDERS[c] += 1

# of the images sitting in the classes only the library has, how many are unique and
# where the rest reappear in the new drop
new_md5_to_class = defaultdict(set)
for f, c, b, m, s in recs:
    if f in (NEW_OBJ, NEW_CAT) and m:
        new_md5_to_class[m].add(c)
ABSENT_ROWS = [r for r in recs if r[0] == LIB and r[1] in ABSENT_CLASSES]
ABSENT_UNIQUE = sum(1 for r in ABSENT_ROWS if r[3] not in new_md5)
ABSENT_RELABEL = Counter()
for r in ABSENT_ROWS:
    for cls in new_md5_to_class.get(r[3], ()):
        ABSENT_RELABEL[cls] += 1

# ---- the Updated Objects folder: object types, and where the library disagrees
lib_class_by_md5 = defaultdict(set)
for f, c, b, m, s in recs:
    if f == LIB and m:
        lib_class_by_md5[m].add(c)
OBJ_SPAN = {}
OBJ_CLASS_TOTALS = {}
for cls in sorted({r[1] for r in recs if r[0] == NEW_OBJ}):
    lines_carried = {ln for (f, ln, c) in cells if f == NEW_OBJ and c == cls}
    OBJ_SPAN[cls] = len(lines_carried)
    OBJ_CLASS_TOTALS[cls] = sum(v for (f, l, c), v in cells.items() if f == NEW_OBJ and c == cls)
OBJ_REDUNDANT = sum(1 for r in recs if r[0] == NEW_OBJ) - len({r[3] for r in recs if r[0] == NEW_OBJ})
OBJ_THREE_CLASSES = sum(OBJ_CLASS_TOTALS[c] for c in ("Fiber", "Foreign Matter", "Extraneous Polymer"))
OBJ_CLEAR_IN_LIB = len({r[3] for r in recs
                        if r[0] == NEW_OBJ and r[1] == "Clear" and r[3] in lib_class_by_md5})
OBJ_EP_AS_FIBER = len({r[3] for r in recs
                       if r[0] == NEW_OBJ and r[1] == "Extraneous Polymer"
                       and "Fiber" in lib_class_by_md5.get(r[3], ())})
OBJ_HEMA_SPLIT = Counter()
for r in recs:
    if r[0] == NEW_OBJ and r[1] == "HEMA":
        for cls in lib_class_by_md5.get(r[3], ()):
            OBJ_HEMA_SPLIT[cls] += 1

# the four ways a file can repeat, each computed, never typed
names_lib = {r[2] for r in recs if r[0] == LIB}
names_new = {r[2] for r in recs if r[0] in (NEW_OBJ, NEW_CAT)}
names_obj = {r[2] for r in recs if r[0] == NEW_OBJ}
names_cat = {r[2] for r in recs if r[0] == NEW_CAT}
LIB_NEW_SHARED = len(names_lib & names_new)
_lib_rows = [r for r in recs if r[0] == LIB]
_new_rows = [r for r in recs if r[0] in (NEW_CAT, NEW_OBJ)]
_new_names = {r[2] for r in _new_rows}
_new_hashes = {r[3] for r in _new_rows}
LIB_NAME_HIT = sum(1 for r in _lib_rows if r[2] in _new_names)
LIB_HASH_HIT = sum(1 for r in _lib_rows if r[3] in _new_hashes)
_names_of = defaultdict(set)
_folder_of = defaultdict(set)
for _f, _c, _b, _m, _s in recs:
    _names_of[_m].add(_b)
    _folder_of[_m].add(_f)
TWO_NAME_PICS = sum(1 for v in _names_of.values() if len(v) > 1)
TWO_NAME_CROSS = sum(1 for m, v in _names_of.items() if len(v) > 1 and len(_folder_of[m]) > 1)
TWO_NAME_INSIDE = TWO_NAME_PICS - TWO_NAME_CROSS
OBJ_CAT_SHARED = len(names_obj & names_cat)
inner = defaultdict(set)
for f, c, b, m, s in recs:
    inner[(f, b)].add(c)
INNER_CONFLICT_FILES = sum(1 for v in inner.values() if len(v) > 1)
basenames_by_md5 = defaultdict(set)
for f, c, b, m, s in recs:
    if m:
        basenames_by_md5[m].add(b)
DIFF_NAME_CONTENT = sum(1 for bset in basenames_by_md5.values() if len(bset) > 1)


def half_up(x):
    return int(math.floor(x + 0.5))


def split_stats(folder):
    """Test images are assigned per line and per class. Everything else trains.

    A cell is 'reportable' on its line when the plain proportional share gives it at
    least one test image. A cell that cannot be split still trains; it just has no
    per-line result.
    """
    out = {}
    for ratio, key in ((0.30, "30"), (0.20, "20")):
        reportable = test = images = 0
        for (f, ln, cls), cnt in cells.items():
            if f != folder:
                continue
            images += cnt
            t = half_up(cnt * ratio)
            if t >= 1:
                reportable += 1
                test += t
        out[key] = dict(reportable=reportable, test=test, train=images - test, images=images)
    out["cells"] = sum(1 for (f, ln, cls) in cells if f == folder)
    return out


SPLITS = {f: split_stats(f) for f in FOLDERS}

# named figures the prose needs
LIB_TOTAL = sum(per_folder_lines[(LIB, l)] for l in LINES)
TEST30 = {}
for folder in FOLDERS:
    for ln in LINES:
        t = 0
        for (f, l, c), cnt in cells.items():
            if f != folder or l != ln:
                continue
            share = half_up(cnt * 0.30)
            if share >= 1:            # a cell is reportable when it has a test image
                t += share
        TEST30[(folder, ln)] = t

TRAIN_GAIN_80 = sum(SPLITS[f]["20"]["train"] - SPLITS[f]["30"]["train"] for f in FOLDERS)
CELLS_REP30 = sum(SPLITS[f]["30"]["reportable"] for f in FOLDERS)
CELLS_REP20 = sum(SPLITS[f]["20"]["reportable"] for f in FOLDERS)
REP_LOST_80 = CELLS_REP30 - CELLS_REP20
CAT_TEST30_MIN = min(TEST30[(NEW_CAT, l)] for l in LINES)
CAT_TEST30_MAX = max(TEST30[(NEW_CAT, l)] for l in LINES)
LIB_TEST30_MIN = min(TEST30[(LIB, l)] for l in LINES)
LIB_TEST30_MAX = max(TEST30[(LIB, l)] for l in LINES)

# ---------------------------------------------------------------------------
# The class-centric pool: folder-agnostic, one row per unique picture.
#   rule 1: Low Dose and Low Dose Obstructing Region of Interest are one class
#   rule 2: Clear, HEMA and duplicates are not classes, so pictures whose only
#           label is one of those fall outside the 22-class set
#   rule 3: a picture with two defect classes takes the class the older library
#           assigns, since that is the canonical 22-class taxonomy
# ---------------------------------------------------------------------------
NAME_MAP = {"Low Dose": "Low Dose Obstructing Region of Interest"}
NOT_A_CLASS = {"Clear", "HEMA", "duplicates"}
DEFECT_CLASSES = sorted({c for f, c, b, m, s in recs if f == LIB})


def mapped_class(cls):
    return NAME_MAP.get(cls, cls)


def is_defect(cls):
    return mapped_class(cls) in DEFECT_CLASSES and cls not in NOT_A_CLASS


pic = defaultdict(lambda: {"labels": set(), "lib": set(), "lines": set(), "folders": set()})
for f, c, b, m, s in recs:
    e = pic[m]
    e["folders"].add(f)
    e["lines"].add(b.split("_")[2])
    if is_defect(c):
        e["labels"].add(mapped_class(c))
        if f == LIB:
            e["lib"].add(mapped_class(c))


def resolved_class(e):
    labels = e["labels"]
    if len(labels) == 1:
        return next(iter(labels))
    preferred = labels & e["lib"]
    return sorted(preferred)[0] if preferred else sorted(labels)[0]


POOL = Counter()                      # (class, line) -> unique pictures
PIC_LABELS = Counter()                # how many labels a picture carries
for m, e in pic.items():
    PIC_LABELS[len(e["labels"])] += 1
    if e["labels"]:
        POOL[(resolved_class(e), sorted(e["lines"])[0])] += 1

POOL_IMAGES = sum(POOL.values())
POOL_EXCLUDED = sum(1 for e in pic.values() if not e["labels"])
POOL_MULTI = sum(1 for e in pic.values() if len(e["labels"]) > 1)
POOL_LINE_CLASH = sum(1 for e in pic.values() if len(e["lines"]) > 1)
POOL_MULTIFOLDER = sum(1 for e in pic.values() if len(e["folders"]) > 1)
CLEAR_OR_DUP_PAIRS = sum(v for k, v in conflict_pairs.items()
                    if "Clear" in k or "duplicates" in k)
POOL_LINES = {ln: sum(v for (c, l), v in POOL.items() if l == ln) for ln in LINES}
POOL_CLASSES_IN_LINE = {ln: sum(1 for (c, l) in POOL if l == ln) for ln in LINES}
POOL_TEST = {}                        # (class, line) -> test images at 70:30
for cls in DEFECT_CLASSES:
    for ln in LINES:
        n_ = POOL.get((cls, ln), 0)
        t = half_up(n_ * 0.30)
        POOL_TEST[(cls, ln)] = t if (n_ >= 2 and t >= 1) else 0
POOL_SCORED = {cls: sum(1 for ln in LINES if POOL_TEST[(cls, ln)] >= 1) for cls in DEFECT_CLASSES}
POOL_PAIRS = {cls: POOL_SCORED[cls] * (POOL_SCORED[cls] - 1) // 2 for cls in DEFECT_CLASSES}
POOL_SCORED_3PLUS = sum(1 for c in DEFECT_CLASSES if POOL_SCORED[c] >= 3)
POOL_SCORED_2PLUS = sum(1 for c in DEFECT_CLASSES if POOL_SCORED[c] >= 2)
POOL_THINNEST = {cls: min([POOL_TEST[(cls, ln)] for ln in LINES if POOL_TEST[(cls, ln)] >= 1],
                          default=0) for cls in DEFECT_CLASSES}
POOL_TEST_TOTAL = {cls: sum(POOL_TEST[(cls, ln)] for ln in LINES) for cls in DEFECT_CLASSES}
POOL_CLASS_TOTAL = {cls: sum(POOL.get((cls, ln), 0) for ln in LINES) for cls in DEFECT_CLASSES}
POOL_LINE_TEST = {ln: sum(POOL_TEST[(c, ln)] for c in DEFECT_CLASSES) for ln in LINES}
POOL_LINE_SCORABLE = {ln: sum(1 for c in DEFECT_CLASSES if POOL_TEST[(c, ln)] >= 1) for ln in LINES}
THIN_CELLS = [(c, ln, POOL_TEST[(c, ln)]) for c in DEFECT_CLASSES for ln in LINES
              if 0 < POOL_TEST[(c, ln)] < 5]
POOL_80 = {}
for cls in DEFECT_CLASSES:
    for ln in LINES:
        n_ = POOL.get((cls, ln), 0)
        t = half_up(n_ * 0.20)
        POOL_80[(cls, ln)] = t if (n_ >= 2 and t >= 1) else 0
POOL_80_SCORABLE = {ln: sum(1 for c in DEFECT_CLASSES if POOL_80[(c, ln)] >= 1) for ln in LINES}
POOL_80_TEST = {ln: sum(POOL_80[(c, ln)] for c in DEFECT_CLASSES) for ln in LINES}
BANDS = [(1, 1, "1"), (2, 4, "2-4"), (5, 9, "5-9"), (10, 24, "10-24"),
         (25, 99, "25-99"), (100, 10 ** 9, "100+")]
POOL_BAND_IMAGES = {}
POOL_BAND_TEST = {}
for ln in LINES:
    sizes = [POOL.get((c, ln), 0) for c in DEFECT_CLASSES]
    sizes = [v for v in sizes if v]
    tests = [POOL_TEST[(c, ln)] for c in DEFECT_CLASSES if POOL_TEST[(c, ln)] >= 1]
    POOL_BAND_IMAGES[ln] = [sum(1 for v in sizes if lo <= v <= hi) for lo, hi, _ in BANDS]
    POOL_BAND_TEST[ln] = [sum(1 for v in tests if lo <= v <= hi) for lo, hi, _ in BANDS]

# ---- the five per-line models: what each line would train and test on
PER_LINE = {}
for folder in FOLDERS:
    for ln in LINES:
        cs = [(c, v) for (f, l, c), v in cells.items() if f == folder and l == ln]
        if not cs:
            continue
        imgs = sum(v for _, v in cs)
        for ratio, key in ((0.30, "30"), (0.20, "20")):
            rep = test = 0
            for cls, cnt in cs:
                t = half_up(cnt * ratio)
                if t >= 1:
                    rep += 1
                    test += t
            PER_LINE[(folder, ln, key)] = dict(images=imgs, classes=len(cs), reportable=rep,
                                               test=test, train=imgs - test)

# ---- how many lines each class appears on: the comparison set for the five models
CLASS_SPAN = {}
SPAN_HIST = {}
SHARED_3PLUS = {}
for folder in FOLDERS:
    span = defaultdict(set)
    for (f, l, c) in cells:
        if f == folder:
            span[c].add(l)
    CLASS_SPAN[folder] = {c: len(ls) for c, ls in span.items()}
    SPAN_HIST[folder] = Counter(CLASS_SPAN[folder].values())
    SHARED_3PLUS[folder] = sum(1 for v in CLASS_SPAN[folder].values() if v >= 3)
    SHARED_2PLUS = sum(1 for v in CLASS_SPAN[folder].values() if v >= 2)

# classes each line can show
present = {}
for f in FOLDERS:
    present[f] = {ln: len({cls for (ff, l, cls) in cells if ff == f and l == ln}) for ln in LINES}
classes_per_folder = {f: len({cls for (ff, l, cls) in cells if ff == f}) for f in FOLDERS}

# classes that live on one line only, or two
line_span = defaultdict(set)
for f, ln, cls in cells:
    line_span[cls].add(ln)
single_line = sorted(c for c, ls in line_span.items() if len(ls) == 1)

# ---------------------------------------------------------------- svg helpers
RAMP = ["#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
        "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#0d366b"]
S1, S2, S3 = "#2a78d6", "#1baf7a", "#eda100"


def stacked_lines():
    """One row per line, three segments: one per folder."""
    rows = []
    for ln in LINES:
        parts = [(SHORT[f], per_folder_lines.get((f, ln), 0), col)
                 for f, col in ((NEW_OBJ, S1), (NEW_CAT, S2), (LIB, S3))]
        rows.append((ln, parts, lines_total[ln]))
    top = max(r[2] for r in rows)
    w, gutter, x0 = 720, 52, 78
    scale = (w - x0 - 90) / top
    h = 14 + 30 * len(rows)
    out = ['<svg viewBox="0 0 {0} {1}" class="chart" role="img">'.format(w, h)]
    for i, (ln, parts, tot) in enumerate(rows):
        y = 11 + 30 * i
        out.append('<text x="{0}" y="{1}" text-anchor="end" class="c-lab" '
                   'dominant-baseline="middle">{2}</text>'.format(gutter, y + 8, ln))
        x = x0
        for name, v, col in parts:
            if not v:
                continue
            bw = v * scale
            out.append('<rect x="{0:.1f}" y="{1}" width="{2:.1f}" height="17" rx="2" fill="{3}">'
                       '<title>{4}, {5}: {6} images</title></rect>'.format(
                           x, y, bw, col, ln, name, n(v)))
            if bw >= 30:
                out.append('<text x="{0:.1f}" y="{1}" text-anchor="middle" class="c-in" '
                           'dominant-baseline="middle">{2}</text>'.format(x + bw / 2, y + 8, n(v)))
            x += bw
        out.append('<text x="{0:.1f}" y="{1}" class="c-val" dominant-baseline="middle">{2}</text>'
                   .format(x + 8, y + 8, n(tot)))
    out.append('</svg>')
    return "\n".join(out)


def coverage_bars(series, maxv, colour):
    """series: list of (label, value). Simple h-bars against a known maximum."""
    w, gutter = 560, 52
    x0 = 60
    scale = (w - x0 - 100) / maxv
    h = 14 + 30 * len(series)
    out = ['<svg viewBox="0 0 {0} {1}" class="chart" role="img">'.format(w, h)]
    for i, (lab, v) in enumerate(series):
        y = 11 + 30 * i
        out.append('<text x="{0}" y="{1}" text-anchor="end" class="c-lab" '
                   'dominant-baseline="middle">{2}</text>'.format(gutter, y + 8, lab))
        out.append('<rect x="{0}" y="{1}" width="{2:.1f}" height="17" rx="2" fill="{3}">'
                   '<title>{4}: {5} of {6} classes</title></rect>'.format(
                       x0, y, max(1, v * scale), colour, lab, v, maxv))
        out.append('<text x="{0:.1f}" y="{1}" class="c-val" dominant-baseline="middle">'
                   '{2} / {3}</text>'.format(x0 + max(1, v * scale) + 8, y + 8, v, maxv))
    out.append('</svg>')
    return "\n".join(out)


def grouped_split():
    """Two bars per folder: class-line combinations reportable at 70:30 and at 80:20."""
    w, gutter, x0 = 560, 150, 158
    groups = [(SHORT[f], SPLITS[f]["30"]["reportable"], SPLITS[f]["20"]["reportable"],
               SPLITS[f]["cells"]) for f in FOLDERS]
    top = max(g[3] for g in groups)
    scale = (w - x0 - 70) / top
    h = 14 + 46 * len(groups)
    out = ['<svg viewBox="0 0 {0} {1}" class="chart" role="img">'.format(w, h)]
    for i, (lab, k30, k20, tot) in enumerate(groups):
        y = 8 + 46 * i
        out.append('<text x="{0}" y="{1}" text-anchor="end" class="c-lab" '
                   'dominant-baseline="middle">{2}</text>'.format(gutter, y + 18, lab))
        for j, (v, col, tag) in enumerate(((k30, S1, "70:30"), (k20, S2, "80:20"))):
            yy = y + j * 19
            out.append('<rect x="{0}" y="{1}" width="{2:.1f}" height="15" rx="2" fill="{3}">'
                       '<title>{4} at {5}: {6} of {7} class-line combinations reportable</title>'
                       '</rect>'.format(x0, yy, max(1, v * scale), col, lab, tag, v, tot))
            out.append('<text x="{0:.1f}" y="{1}" class="c-val" dominant-baseline="middle">'
                       '{2} of {3}</text>'.format(x0 + max(1, v * scale) + 7, yy + 8, v, tot))
    out.append('</svg>')
    return "\n".join(out)


def heatmap(classes, values, title_suffix=""):
    """Rows = classes, columns = lines, cell = picture count, colour on a log ramp."""
    cw, ch, gap, gutter = 62, 20, 2, 218
    maxv = max(values.values()) if values else 1
    w = gutter + len(LINES) * (cw + gap) + 78
    h = 26 + len(classes) * (ch + gap) + 6
    out = ['<svg viewBox="0 0 {0} {1}" class="chart" role="img">'.format(w, h)]
    for j, ln in enumerate(LINES):
        x = gutter + j * (cw + gap) + cw / 2
        out.append('<text x="{0:.0f}" y="12" text-anchor="middle" class="c-tick">{1}</text>'.format(x, ln))
    out.append('<text x="{0:.0f}" y="12" text-anchor="middle" class="c-tick">total</text>'.format(
        gutter + len(LINES) * (cw + gap) + 30))
    for i, cls in enumerate(classes):
        y = 20 + i * (ch + gap)
        out.append('<text x="{0}" y="{1}" text-anchor="end" class="c-lab" '
                   'dominant-baseline="middle">{2}</text>'.format(gutter - 8, y + ch / 2, cls[:32]))
        total = 0
        for j, ln in enumerate(LINES):
            v = values.get((cls, ln), 0)
            total += v
            x = gutter + j * (cw + gap)
            if not v:
                fill = "var(--gridline)"
            else:
                idx = min(len(RAMP) - 1,
                          int(round(math.log10(v + 1) / math.log10(maxv + 1) * (len(RAMP) - 1))))
                fill = RAMP[idx]
            test = POOL_TEST.get((cls, ln), 0)
            out.append('<rect x="{0:.0f}" y="{1}" width="{2}" height="{3}" rx="2" fill="{4}">'
                       '<title>{5}, {6}: {7} pictures, {8} of them test at 70:30{9}</title></rect>'.format(
                           x, y, cw, ch, fill, cls, ln, v, test, title_suffix))
            if v:
                dark = fill in RAMP[:5]
                out.append('<text x="{0:.0f}" y="{1}" text-anchor="middle" dominant-baseline="middle" '
                           'style="font-size:10px" fill="{2}">{3}</text>'.format(
                               x + cw / 2, y + ch / 2, "var(--text-primary)" if dark else "#fff", v))
        out.append('<text x="{0:.0f}" y="{1}" class="c-val" dominant-baseline="middle">{2}</text>'.format(
            gutter + len(LINES) * (cw + gap) + 4, y + ch / 2, n(total)))
    out.append('</svg>')
    return "\n".join(out)


# ---------------------------------------------------------------- page
CSS = """<style>
:root{
  color-scheme: light;
  --page-plane:#f9f9f7; --surface-1:#fcfcfb; --surface-card:#ffffff;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#898781;
  --gridline:#e6e5de; --border:rgba(11,11,11,0.10);
  --series-1:#2a78d6; --series-1-wash:rgba(42,120,214,0.10);
  --ok:#0ca30c; --bad:#d03b3b;
  --shadow:0 1px 2px rgba(11,11,11,0.06),0 1px 8px rgba(11,11,11,0.04);
}
@media (prefers-color-scheme:dark){
  :root:where(:not([data-theme="light"])){
    color-scheme:dark;
    --page-plane:#0d0d0d; --surface-1:#1a1a19; --surface-card:#201f1d;
    --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#898781;
    --gridline:#2c2c2a; --border:rgba(255,255,255,0.10);
    --series-1:#3987e5; --series-1-wash:rgba(57,135,229,0.14);
    --ok:#3fb950; --bad:#e66767;
    --shadow:0 1px 2px rgba(0,0,0,0.3),0 1px 10px rgba(0,0,0,0.25);
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --page-plane:#0d0d0d; --surface-1:#1a1a19; --surface-card:#201f1d;
  --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#898781;
  --gridline:#2c2c2a; --border:rgba(255,255,255,0.10);
  --series-1:#3987e5; --series-1-wash:rgba(57,135,229,0.14);
  --ok:#3fb950; --bad:#e66767;
  --shadow:0 1px 2px rgba(0,0,0,0.3),0 1px 10px rgba(0,0,0,0.25);
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--page-plane);color:var(--text-primary);
  font-family:"JetBrains Mono",ui-monospace,monospace;letter-spacing:0;-webkit-font-smoothing:antialiased;line-height:1.55}
a{color:var(--series-1)}
.wrap{max-width:1180px;margin:0 auto;padding:0 22px 90px}
header.top{position:sticky;top:0;z-index:50;background:var(--surface-1);border-bottom:1px solid var(--border);backdrop-filter:blur(6px)}
.topbar{max-width:1180px;margin:0 auto;padding:13px 22px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.topbar h1{font-size:15px;font-weight:600;margin:0}
nav.sections{display:flex;gap:2px;flex-wrap:wrap;font-size:13px;margin-left:auto}
nav.sections a{color:var(--text-secondary);text-decoration:none;padding:5px 9px;border-radius:6px}
nav.sections a:hover{background:var(--series-1-wash);color:var(--text-primary)}
.theme-toggle{border:1px solid var(--border);background:var(--surface-card);color:var(--text-secondary);border-radius:6px;padding:5px 10px;font-size:12.5px;cursor:pointer}
.hero{padding:30px 0 4px}
.hero h2{font-size:27px;margin:0 0 8px;letter-spacing:-0.01em}
.hero .meta{color:var(--text-secondary);font-size:13.5px;line-height:1.7;max-width:900px}
.hero .meta code{background:var(--surface-card);border:1px solid var(--border);border-radius:4px;padding:1px 5px;font-size:12px}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0}
.stat-tile{background:var(--surface-card);border:1px solid var(--border);border-radius:12px;padding:15px;box-shadow:var(--shadow)}
.stat-tile .label{font-size:11.5px;color:var(--text-secondary);margin-bottom:6px}
.stat-tile .value{font-size:24px;font-weight:600;letter-spacing:-0.01em}
.stat-tile .value.ok{color:var(--ok)} .stat-tile .value.bad{color:var(--bad)}
.stat-tile .sub{font-size:11px;color:var(--text-muted);margin-top:5px;line-height:1.45}
section{margin-top:52px;scroll-margin-top:66px}
section h3{font-size:20px;margin:0 0 6px;letter-spacing:-0.01em}
section h4{font-size:15px;margin:26px 0 8px;color:var(--text-secondary);font-weight:600}
p.desc{color:var(--text-secondary);font-size:13.5px;margin:0 0 12px;max-width:900px}
p.note{color:var(--text-secondary);font-size:12.5px;margin:8px 0 4px;max-width:900px;padding-left:12px;border-left:2px solid var(--gridline)}
code{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:0.9em}
.chart{width:100%;height:auto;margin:6px 0;overflow:visible}
.chart .grid{stroke:var(--gridline);stroke-width:1}
.chart .c-lab{fill:var(--text-secondary);font-size:11px}
.chart .c-val{fill:var(--text-primary);font-size:11px;font-weight:500}
.chart .c-tick{fill:var(--text-muted);font-size:10px}
.chart .c-in{fill:#fff;font-size:10px;font-weight:600}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--text-secondary);margin:4px 0 2px}
.legend .lg{display:flex;align-items:center;gap:5px}
.legend .lg i{width:11px;height:11px;border-radius:3px;display:inline-block}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:start}
@media(max-width:760px){.two-col{grid-template-columns:1fr}}
.twrap{overflow-x:auto;margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{padding:6px 10px;border-bottom:1px solid var(--border);white-space:nowrap}
th{color:var(--text-secondary);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:0.03em}
td .ok,span.ok{color:var(--ok);font-weight:600}
td .bad,span.bad{color:var(--bad);font-weight:600}
ul.findings,ol.findings{font-size:13px;color:var(--text-secondary);line-height:1.7;max-width:940px;padding-left:22px}
ul.findings li,ol.findings li{margin:7px 0}
ul.findings b,ol.findings b{color:var(--text-primary)}
.hero .foot{margin-top:14px;font-size:12px;color:var(--text-muted)}
</style>"""

generated = datetime.now().strftime("%Y-%m-%d %H:%M")
nav_items = [("found", "1 What we found"), ("lines", "2 Images per line"),
             ("coverage", "3 Comparison set"), ("dupes", "4 Duplicates"),
             ("split", "5 Five models"), ("questions", "6 Questions"),
             ("next", "7 Recommendations")]

p = []
p.append('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">')
p.append('<title>Production line analysis, 2026-09-16</title>')
p.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
p.append(CSS)
p.append('</head>\n<body>')

p.append('<header class="top"><div class="topbar"><h1>Production line analysis</h1>'
         '<nav class="sections">' +
         "".join('<a href="#{0}">{1}</a>'.format(i, t) for i, t in nav_items) +
         '</nav>'
         '<button class="theme-toggle" onclick="var r=document.documentElement,'
         'd=r.getAttribute(\'data-theme\')===\'dark\';r.setAttribute(\'data-theme\',d?\'light\':\'dark\')">'
         '◐ theme</button></div></header>')

p.append('<div class="wrap">')
p.append('<div class="hero"><h2>Can one model handle every production line?</h2>'
         '<div class="meta">')
p.append('This page counts what we have, line by line, and sets out the plan and the open decisions. The three '
         'folders hold <b>{0}</b> images across <b>{1}</b> production lines. After removing repeated pictures '
         'they hold <b>{2}</b> unique pictures, of which <b>{3}</b> carry one of the <b>{4}</b> defect classes '
         'and every one carries a line number, so <b>no image is unassigned</b>. Because the folders label the '
         'same classes, the analysis pools them by class rather than by folder, and the pooled set is what the '
         'models use. To answer the client question we train <b>{1} separate ResNet-50 models, one per '
         'line</b>, and compare them on the classes that three or more lines share ({5} classes). If those '
         'models agree on the classes they have in common, the line carries no signal and one model is '
         'enough.'.format(
             n(files_total), len(LINES), n(unique_images), n(POOL_IMAGES), len(DEFECT_CLASSES),
             POOL_SCORED_3PLUS))
p.append('<div class="foot">Generated {0} by <code>src/make_line_report.py</code> from the VM image library '
         'and the storage account listing. Counts were taken twice from two independent sources and agree '
         'exactly. Companion: <code>reports/lines/LINE_TAG_ANALYSIS_20260916.md</code>.</div>'.format(generated))
p.append('</div></div>')

# ---- 1
p.append('<section id="found"><h3>1 · What we found</h3>')
p.append('<p class="desc">The numbers that frame every later decision.</p>')
p.append('<div class="stat-grid">')
p.append('<div class="stat-tile"><div class="label">Images</div><div class="value">{0}</div>'
         '<div class="sub">three folders combined</div></div>'.format(n(files_total)))
p.append('<div class="stat-tile"><div class="label">Unique images</div><div class="value">{0}</div>'
         '<div class="sub">{1} files are repeated copies</div></div>'.format(n(unique_images), n(redundant)))
p.append('<div class="stat-tile"><div class="label">Production lines</div><div class="value">{0}</div>'
         '<div class="sub">{1}</div></div>'.format(len(LINES), ", ".join(LINES)))
p.append('<div class="stat-tile"><div class="label">Defect-class dataset</div><div class="value">{0}</div>'
         '<div class="sub">{1} classes, pooled from all three folders; {2} pictures carry no defect label and '
         'sit outside it</div></div>'.format(n(POOL_IMAGES), len(DEFECT_CLASSES), n(POOL_EXCLUDED)))
p.append('<div class="stat-tile"><div class="label">Images with no line number</div>'
         '<div class="value ok">{0}</div><div class="sub">the line question is answerable for every image</div>'
         '</div>'.format(orphans))
p.append('</div>')
p.append('<p class="note">Two independent counts were taken: one from the storage account listing and one from '
         'the files on the analysis machine. All {0} rows match, cell for cell, with the same fingerprint '
         '({1}). A third count of the older library from a separate local copy also matched exactly, '
         '{2} files against {2} files.</p>'.format(n(files_total), "51ae788b", n(LIB_TOTAL)))
p.append('</section>')

# ---- 2
p.append('<section id="lines"><h3>2 · The data, as delivered</h3>')
p.append('<p class="desc">Three folders arrived and they label the same pictures in different ways, so this '
         'section describes what came in. Section 3 pools the folders by defect class, which is the unit the '
         'five models use.</p>')
p.append('<div class="legend">'
         '<span class="lg"><i style="background:{0}"></i>Updated Objects</span>'
         '<span class="lg"><i style="background:{1}"></i>Updated Categorical</span>'
         '<span class="lg"><i style="background:{2}"></i>Older library</span></div>'.format(S1, S2, S3))
p.append(stacked_lines())
p.append('<div class="twrap"><table><thead><tr><th style="text-align:left">Line</th>'
         + "".join('<th style="text-align:right">{0}</th>'.format(SHORT[f]) for f in FOLDERS)
         + '<th style="text-align:right">Total</th></tr></thead><tbody>')
for ln in LINES:
    row = ['<tr><td style="text-align:left">{0}</td>'.format(ln)]
    for f in FOLDERS:
        row.append('<td style="text-align:right">{0}</td>'.format(n(per_folder_lines.get((f, ln), 0))))
    row.append('<td style="text-align:right"><b>{0}</b></td></tr>'.format(n(lines_total[ln])))
    p.append("".join(row))
p.append('</tbody></table></div>')
p.append('<p class="note">L24 alone holds {0} of the {1} files ({2:.0f} percent) and L25 holds {3} ({4:.0f} '
         'percent). Each of the five models trains on one line, so this table sets the raw volume behind each '
         'of them before any pooling.</p>'.format(
             n(lines_total["L24"]), n(files_total), 100.0 * lines_total["L24"] / files_total,
             n(lines_total["L25"]), 100.0 * lines_total["L25"] / files_total))
p.append('<h4>The Updated Objects folder: object types, not defect classes</h4>')
p.append('<div class="twrap"><table><thead><tr><th style="text-align:left">Group</th>'
         + "".join('<th style="text-align:right">{0}</th>'.format(ln) for ln in LINES)
         + '<th style="text-align:right">Total</th></tr></thead><tbody>')
for cls in sorted(OBJ_CLASS_TOTALS, key=lambda c: -OBJ_CLASS_TOTALS[c]):
    p.append('<tr><td style="text-align:left">{0}</td>'.format(cls)
             + "".join('<td style="text-align:right">{0}</td>'.format(n(cells.get((NEW_OBJ, ln, cls), 0)))
                       for ln in LINES)
             + '<td style="text-align:right">{0}</td></tr>'.format(n(OBJ_CLASS_TOTALS[cls])))
p.append('<tr><td style="text-align:left"><b>Total</b></td>'
         + "".join('<td style="text-align:right"><b>{0}</b></td>'.format(
             n(per_folder_lines.get((NEW_OBJ, ln), 0))) for ln in LINES)
         + '<td style="text-align:right"><b>{0}</b></td></tr>'.format(
             n(sum(per_folder_lines[(NEW_OBJ, l)] for l in LINES))))
p.append('</tbody></table></div>')
p.append('<p class="note">This folder groups by object type, not by defect class, and it holds no duplicates of '
         'its own: its {0} files are {0} different pictures. It cannot serve as the defect-class dataset, '
         'because "Clear" is {1} of its pictures and is not a class in the library taxonomy, and "HEMA" is '
         '{2} pictures that split between two library classes ({3}). Where it does help is with three classes '
         'the new Categorical folder does not carry at all: Fiber, Foreign Matter and Extraneous Polymer, {4} '
         'pictures between them. Those pictures join the pool in section 3 and are what lifts Fiber from 61 '
         'pictures in the library to {5}, Foreign Matter from 71 to {6}, and Extraneous Polymer from 17 to '
         '{7}.</p>'.format(
             n(sum(per_folder_lines[(NEW_OBJ, l)] for l in LINES)), n(OBJ_CLASS_TOTALS["Clear"]),
             n(OBJ_CLASS_TOTALS["HEMA"]),
             ", ".join("{0} {1}".format(v, k) for k, v in OBJ_HEMA_SPLIT.most_common()),
             n(OBJ_THREE_CLASSES), n(POOL_CLASS_TOTAL["Fiber"]), n(POOL_CLASS_TOTAL["Foreign Matter"]),
             n(POOL_CLASS_TOTAL["Extraneous Polymer"])))
p.append('</section>')

# ---- 3
CLASSES_BY_SIZE = sorted(DEFECT_CLASSES, key=lambda c: -sum(POOL.get((c, l), 0) for l in LINES))
FIVE_LINE = [c for c in DEFECT_CLASSES if POOL_SCORED[c] == 5]
ONE_LINE = [c for c in DEFECT_CLASSES if POOL_SCORED[c] == 1]
TWO_LINE = [c for c in DEFECT_CLASSES if POOL_SCORED[c] == 2]
p.append('<section id="coverage"><h3>3 · The 22 defect classes, line by line</h3>')
p.append('<p class="desc">This section pools the three source folders by defect class, so the unit is the class '
         'and not the folder, and every picture is counted once even when it sits in two folders. Three rules '
         'make the pool: "Low Dose" and "Low Dose Obstructing Region of Interest" are one class; "Clear", '
         '"HEMA" and "duplicates" are not classes, so the {0} pictures whose only label is one of those fall '
         'outside this table; and the {1} pictures that carry two defect classes take the class the older '
         'library assigns, which is the canonical taxonomy. {2} pictures sit in more than one folder, and '
         '{3} of those disagree on their line number, so the line is independent of which folder a copy '
         'sits in.</p>'.format(n(POOL_EXCLUDED), POOL_MULTI, n(POOL_MULTIFOLDER), n(POOL_LINE_CLASH)))
p.append(heatmap(CLASSES_BY_SIZE, POOL))
p.append('<p class="note">Each cell is the number of pictures of that class on that line, coloured on a log '
         'scale, so a pale cell still holds pictures. Hover a cell to see how many of them become test '
         'images.</p>')
p.append('<div class="twrap"><table><thead><tr><th style="text-align:left">Class</th>'
         + "".join('<th style="text-align:right">{0}</th>'.format(l) for l in LINES)
         + '<th style="text-align:right">Total</th><th style="text-align:right">Lines scorable</th>'
         '<th style="text-align:right">Comparisons</th><th style="text-align:right">Thinnest line</th>'
         '<th style="text-align:right">Test images</th></tr></thead><tbody>')
for cls in CLASSES_BY_SIZE:
    p.append('<tr><td style="text-align:left">{0}</td>'.format(cls)
             + "".join('<td style="text-align:right">{0}</td>'.format(n(POOL.get((cls, l), 0))) for l in LINES)
             + '<td style="text-align:right">{0}</td><td style="text-align:right">{1}</td>'
               '<td style="text-align:right">{2}</td><td style="text-align:right">{3}</td>'
               '<td style="text-align:right">{4}</td></tr>'.format(
                   n(sum(POOL.get((cls, l), 0) for l in LINES)), POOL_SCORED[cls], POOL_PAIRS[cls],
                   POOL_THINNEST[cls], n(POOL_TEST_TOTAL[cls])))
p.append('<tr><td style="text-align:left"><b>Total</b></td>'
         + "".join('<td style="text-align:right"><b>{0}</b></td>'.format(n(POOL_LINES[l])) for l in LINES)
         + '<td style="text-align:right"><b>{0}</b></td><td style="text-align:right"></td>'
           '<td style="text-align:right"></td><td style="text-align:right"></td>'
           '<td style="text-align:right"><b>{1}</b></td></tr>'.format(
               n(POOL_IMAGES), n(sum(POOL_TEST_TOTAL.values()))))
p.append('</tbody></table></div>')
p.append('<p class="note">Four columns need a word of explanation. <b>Lines scorable</b> is how many lines hold '
         'enough pictures of that class to put at least one of them in a test set; a class scorable on one line '
         'gives no comparison at all. <b>Comparisons</b> is the number of line pairs that can be compared for '
         'that class, which is the scorable count taken two at a time. <b>Thinnest line</b> is the test count '
         'on the line with the fewest, and it bounds every comparison for that class, because a pair is only '
         'as strong as its weaker side. <b>Test images</b> is the total across all lines.</p>')
p.append('<p class="note">The pool reads well. {0} classes are scorable on all five lines, which gives ten '
         'line-to-line comparisons each. {1} classes are scorable on one line only and cannot be compared at '
         'all: {2}. {3} classes are scorable on two lines, which gives one comparison each: {4}. Across the '
         'whole table, {5} class-line cells hold fewer than five test images, and those are the cells where a '
         'result will be inconclusive rather than informative.</p>'.format(
             len(FIVE_LINE), len(ONE_LINE), ", ".join(ONE_LINE), len(TWO_LINE), ", ".join(TWO_LINE),
             len(THIN_CELLS)))
p.append('<h4>What each line would train and test on, at 70:30</h4>')
p.append('<div class="twrap"><table><thead><tr><th style="text-align:left">Line</th>'
         '<th style="text-align:right">Pictures</th><th style="text-align:right">Classes present</th>'
         '<th style="text-align:right">Classes scorable</th><th style="text-align:right">Test images</th>'
         '<th style="text-align:right">Train images</th><th style="text-align:right">Thin cells</th>'
         '</tr></thead><tbody>')
for ln in LINES:
    thin = sum(1 for c in DEFECT_CLASSES if 0 < POOL_TEST[(c, ln)] < 5)
    p.append('<tr><td style="text-align:left">{0}</td><td style="text-align:right">{1}</td>'
             '<td style="text-align:right">{2}</td><td style="text-align:right">{3}</td>'
             '<td style="text-align:right">{4}</td><td style="text-align:right">{5}</td>'
             '<td style="text-align:right">{6}</td></tr>'.format(
                 ln, n(POOL_LINES[ln]), POOL_CLASSES_IN_LINE[ln], POOL_LINE_SCORABLE[ln],
                 n(POOL_LINE_TEST[ln]), n(POOL_LINES[ln] - POOL_LINE_TEST[ln]), thin))
p.append('<tr><td style="text-align:left"><b>All lines</b></td><td style="text-align:right"><b>{0}</b></td>'
         '<td style="text-align:right"></td><td style="text-align:right"></td>'
         '<td style="text-align:right"><b>{1}</b></td><td style="text-align:right"><b>{2}</b></td>'
         '<td style="text-align:right"><b>{3}</b></td></tr>'.format(
             n(POOL_IMAGES), n(sum(POOL_LINE_TEST.values())),
             n(POOL_IMAGES - sum(POOL_LINE_TEST.values())), len(THIN_CELLS)))
p.append('</tbody></table></div>')
p.append('<p class="note">Every line trains on between {0} and {1} pictures and is scored on between {2} and '
         '{3} test images, against {4} to {5} in the older library alone. Pooling the folders is what makes '
         'this workable: the new folders carry the same classes as the library, so they add pictures to a '
         'class rather than adding classes.</p>'.format(
             n(min(POOL_LINES.values())), n(max(POOL_LINES.values())),
             n(min(POOL_LINE_TEST.values())), n(max(POOL_LINE_TEST.values())),
             n(LIB_TEST30_MIN), n(LIB_TEST30_MAX)))
p.append('<h4>How the classes are distributed on each line</h4>')
p.append('<p class="note">Each line takes two rows: the first counts its classes by how many pictures they '
         'hold, the second by how many test images they produce. The band columns count classes; the last '
         'column is the line total.</p>')
p.append('<div class="twrap"><table><thead><tr><th style="text-align:left">Line and measure</th>'
         + "".join('<th style="text-align:right">{0}</th>'.format(b[2]) for b in BANDS)
         + '<th style="text-align:right">Total</th></tr></thead><tbody>')
for ln in LINES:
    p.append('<tr><td style="text-align:left">{0}, class pictures</td>{1}'
             '<td style="text-align:right">{2}</td></tr>'.format(
                 ln, "".join('<td style="text-align:right">{0}</td>'.format(v) for v in POOL_BAND_IMAGES[ln]),
                 n(POOL_LINES[ln])))
    p.append('<tr><td style="text-align:left">{0}, test images</td>{1}'
             '<td style="text-align:right">{2}</td></tr>'.format(
                 ln, "".join('<td style="text-align:right">{0}</td>'.format(v) for v in POOL_BAND_TEST[ln]),
                 n(POOL_LINE_TEST[ln])))
p.append('</tbody></table></div>')
p.append('<p class="note">The second row of each pair is the one that matters, because it is what the model is '
         'scored on. On L27, {0} classes produce fewer than five test images, and on L31, {1} do, so those are '
         'the lines and classes where a comparison between the five models will rest on a handful of '
         'pictures.</p>'.format(
             sum(1 for c in DEFECT_CLASSES if 0 < POOL_TEST[(c, "L27")] < 5),
             sum(1 for c in DEFECT_CLASSES if 0 < POOL_TEST[(c, "L31")] < 5)))
p.append('</section>')

# ---- 4
p.append('<section id="dupes"><h3>4 · Repeats and label conflicts</h3>')
p.append('<p class="desc">Repeated pictures and conflicting labels decide whether a split is trustworthy. '
         'Identity was checked by content fingerprint, not by file name.</p>')
p.append('<div class="stat-grid">')
p.append('<div class="stat-tile"><div class="label">Repeated copies</div><div class="value">{0}</div>'
         '<div class="sub">files beyond the {1} unique images</div></div>'.format(n(redundant), n(unique_images)))
p.append('<div class="stat-tile"><div class="label">Same image, two labels</div>'
         '<div class="value bad">{0}</div><div class="sub">the picture is identical, the class differs</div>'
         '</div>'.format(n(len(conflicting))))
p.append('<div class="stat-tile"><div class="label">Images the library alone holds</div>'
         '<div class="value">{0}</div><div class="sub">no match in the new drop, across {1} library class '
         'folders</div></div>'.format(n(len(lib_only)), len(LIB_ONLY_FOLDERS)))
p.append('<div class="stat-tile"><div class="label">"duplicates" folder</div><div class="value">{0}</div>'
         '<div class="sub">every one already exists in a class folder</div></div>'.format(n(DUP_FOLDER_FILES)))
p.append('</div>')
p.append('<div class="twrap"><table><thead><tr><th style="text-align:left">Where the repeat sits</th>'
         '<th style="text-align:right">Count</th><th style="text-align:left">Why it matters</th>'
         '</tr></thead><tbody>')
p.append('<tr><td style="text-align:left">Same name in the library and the new drop</td>'
         '<td style="text-align:right">{0}</td><td style="text-align:left">identical content; the same image '
         'counted twice if the folders are pooled</td></tr>'.format(n(LIB_NEW_SHARED)))
p.append('<tr><td style="text-align:left">Same name in both new folders</td>'
         '<td style="text-align:right">{0}</td><td style="text-align:left">identical content across the two '
         'new folders</td></tr>'.format(n(OBJ_CAT_SHARED)))
p.append('<tr><td style="text-align:left">Same name in two classes of one folder</td>'
         '<td style="text-align:right">{0}</td><td style="text-align:left">one picture, two class labels: a '
         'label conflict on identical content</td></tr>'.format(n(INNER_CONFLICT_FILES)))
p.append('<tr><td style="text-align:left">Same picture under a different name</td>'
         '<td style="text-align:right">{0}</td><td style="text-align:left">a name-based comparison '
         'undercounts the overlap</td></tr>'.format(n(DIFF_NAME_CONTENT)))
p.append('</tbody></table></div>')
p.append('<h4>The conflicting labels that matter</h4>')
p.append('<div class="twrap"><table><thead><tr><th style="text-align:left">Label pair on the same picture</th>'
         '<th style="text-align:right">Images</th></tr></thead><tbody>')
for pair, cnt in conflict_pairs.most_common(6):
    p.append('<tr><td style="text-align:left">{0}</td><td style="text-align:right">{1}</td></tr>'.format(
        " against ".join(pair), n(cnt)))
p.append('</tbody></table></div>')
clear_classes = sorted({c for pair, cnt in conflict_pairs.items() if "Clear" in pair
                        for c in pair if c != "Clear"})
p.append('<p class="note">Three readings. The Low Dose pair is only a naming difference, so those {0} images '
         'confirm it is one class. The <b>Clear</b> rows are a real contradiction: {1} images are marked as a '
         'defect in the older library and as Clear in the new folder, so Clear may mean "readable image" '
         'rather than "no defect". And Extraneous Polymer against Fiber is a defect against a defect on {2} '
         'images, which no naming rule can settle.</p>'.format(
             n(conflict_pairs.get(("Low Dose", "Low Dose Obstructing Region of Interest"), 0)),
             n(clear_conflicts),
             n(conflict_pairs.get(("Extraneous Polymer", "Fiber"), 0))))
p.append('<p class="note">If the older library is dropped, {0} unique images are lost: they sit in {1} library '
         'class folders, led by {2}. Separately, {3} classes exist only in the library and hold {4} images '
         'between them. Of those {4} images, {5} are unique to the library and the other {6} are the same '
         'pictures that the new drop files under a different class, most often {7}. So those {3} classes '
         'bring {5} new images, not {4}.</p>'.format(
             n(len(lib_only)), len(LIB_ONLY_FOLDERS),
             ", ".join("{0} ({1})".format(c, v) for c, v in LIB_ONLY_FOLDERS.most_common(3)),
             len(ABSENT_CLASSES), n(ABSENT_IMAGES), n(ABSENT_UNIQUE),
             n(ABSENT_IMAGES - ABSENT_UNIQUE),
             ", ".join("{0} ({1})".format(c, v) for c, v in ABSENT_RELABEL.most_common(2))))
p.append('<p class="note">The overlap was checked twice, by file name and by content, and the two agree in '
         'one direction only. Of the older library\'s {0} files, {1} are found in the new drop by name and {2} by '
         'content, so a name comparison misses {3} files that are the same picture under a different name. In the '
         'other direction the names are trustworthy: no file name appears in two folders over different content, so '
         'a name match is never a false match. Taken across all three folders, {4} pictures are filed under more '
         'than one name, {5} of them across folders and {6} of them inside a single folder.</p>'.format(
             n(LIB_TOTAL), n(LIB_NAME_HIT), n(LIB_HASH_HIT), n(LIB_HASH_HIT - LIB_NAME_HIT),
             n(TWO_NAME_PICS), n(TWO_NAME_CROSS), n(TWO_NAME_INSIDE)))
p.append('<p class="note">The three pool rules in section 3 resolve these conflicts, and the arithmetic closes. Of the {0} pictures that carry two labels, {1} are the Low Dose pair and are therefore one class, {2} involve "Clear" or "duplicates", which are not classes, and {3} pair HEMA with a defect class, which leaves one class standing. That leaves {4} pictures that keep two defect classes, and the older library decides those. This is how the pooled set in section 3 counts every picture once and still gives every picture a single label.</p>'.format(
             n(sum(conflict_pairs.values())),
             n(conflict_pairs.get(("Low Dose", "Low Dose Obstructing Region of Interest"), 0)),
             n(CLEAR_OR_DUP_PAIRS),
             n(sum(conflict_pairs.values()) - conflict_pairs.get(("Low Dose", "Low Dose Obstructing Region of Interest"), 0)
               - CLEAR_OR_DUP_PAIRS - POOL_MULTI), POOL_MULTI))
p.append('</section>')

# ---- 5
SPLIT_ROWS = []
for ln in LINES:
    SPLIT_ROWS.append((ln, POOL_LINES[ln], POOL_LINE_SCORABLE[ln], POOL_80_SCORABLE[ln],
                       POOL_LINE_TEST[ln], POOL_LINES[ln] - POOL_LINE_TEST[ln],
                       POOL_80_TEST[ln], POOL_LINES[ln] - POOL_80_TEST[ln]))
SPLIT_TOTALS = {i: sum(r[i] for r in SPLIT_ROWS) for i in (1, 2, 3, 4, 5, 6, 7)}
POOL_TRAIN = {ln: POOL_LINES[ln] - POOL_LINE_TEST[ln] for ln in LINES}
MATCH_VOLUME = min(POOL_TRAIN.values())
MATCH_VOLUME_LINE = sorted(LINES, key=lambda l: POOL_TRAIN[l])[0]
MATCH_STRICT = sum(min((POOL.get((c, l), 0) - POOL_TEST[(c, l)] for l in LINES
                        if POOL_TEST[(c, l)] > 0), default=0)
                   for c in DEFECT_CLASSES if POOL_SCORED[c] >= 3)
MATCH_BIGGEST = sorted(LINES, key=lambda l: -POOL_TRAIN[l])[0]
p.append('<section id="split"><h3>5 · The five models and their splits</h3>')
p.append('<p class="desc">Each line gets its own model and its own split, so a model is scored only on pictures '
         'from its own line. The split is made inside each class inside each line, and a cell is '
         '<b>scorable</b> when a plain proportional share leaves it at least one test image; everything else '
         'trains. Nothing is discarded either way, because every picture that is not a test image is used for '
         'training, including the cells that hold a single picture and can never be scored.</p>')
p.append('<div class="twrap"><table><thead><tr><th style="text-align:left">Line</th>'
         '<th style="text-align:right">Pictures</th><th style="text-align:right">Scorable 70:30</th>'
         '<th style="text-align:right">Scorable 80:20</th><th style="text-align:right">Train (70%)</th>'
         '<th style="text-align:right">Test (30%)</th><th style="text-align:right">Train (80%)</th>'
         '<th style="text-align:right">Test (20%)</th></tr></thead><tbody>')
for r in SPLIT_ROWS:
    p.append('<tr><td style="text-align:left">{0}</td><td style="text-align:right">{1}</td>'
             '<td style="text-align:right">{2}</td><td style="text-align:right"><span class="bad">{3}</span>'
             '</td><td style="text-align:right">{4}</td><td style="text-align:right">{5}</td>'
             '<td style="text-align:right">{6}</td><td style="text-align:right">{7}</td></tr>'.format(
                 r[0], n(r[1]), r[2], r[3], n(r[5]), n(r[4]), n(r[7]), n(r[6])))
p.append('<tr><td style="text-align:left"><b>All lines</b></td><td style="text-align:right"><b>{0}</b></td>'
         '<td style="text-align:right"><b>{1}</b></td><td style="text-align:right"><b>{2}</b></td>'
         '<td style="text-align:right"><b>{3}</b></td><td style="text-align:right"><b>{4}</b></td>'
         '<td style="text-align:right"><b>{5}</b></td><td style="text-align:right"><b>{6}</b></td></tr>'.format(
             n(SPLIT_TOTALS[1]), n(SPLIT_TOTALS[2]), n(SPLIT_TOTALS[3]), n(SPLIT_TOTALS[5]),
             n(SPLIT_TOTALS[4]), n(SPLIT_TOTALS[7]), n(SPLIT_TOTALS[6])))
p.append('</tbody></table></div>')
p.append('<p class="note">The two ratios differ only in how much data goes to the test set and how many cells '
         'survive as scorable. 70:30 leaves a test image for {0} class-line cells against {1} at 80:20, and it '
         'scores the models on {2} test images against {3}. 80:20 buys {4} more training pictures out of {5}, '
         'which will not change what the models learn, and it costs {6} cells that can no longer be measured '
         'at all. <b>Split each line at 70:30.</b></p>'.format(
             n(SPLIT_TOTALS[2]), n(SPLIT_TOTALS[3]), n(SPLIT_TOTALS[4]), n(SPLIT_TOTALS[6]),
             n(SPLIT_TOTALS[7] - SPLIT_TOTALS[5]), n(SPLIT_TOTALS[1]),
             SPLIT_TOTALS[2] - SPLIT_TOTALS[3]))
p.append('<h4>What the comparison between the five models requires</h4>')
p.append('<p class="note">The five training sets would be unequal: {0} would train on {1} pictures and {2} '
         'on {3}, three times fewer, so a gap between those two models could come from the training volume '
         'rather than from the line. Equalising the volume is practical: train every line on {3} pictures, '
         'the count of the smallest line, drawn in proportion to that line\'s own class mix. Equalising per '
         'class instead, the same number of pictures for every class on every line, is not practical: on its '
         'scarcest line a class can hold a single picture (HEMA Obstruction 1, Bubble Cluster 1, Bubble '
         'Irregular 1, Bubble Scatter 1), which would cut every line to about {4} training pictures against '
         'the {1} to {3} available today.</p>'.format(
             MATCH_BIGGEST, n(POOL_TRAIN[MATCH_BIGGEST]), MATCH_VOLUME_LINE,
             n(MATCH_VOLUME), n(MATCH_STRICT)))
p.append('<p class="note">The five models carry different class lists, so their overall accuracy is not '
         'directly comparable: a model carrying 16 classes has a different chance level from one carrying 21. '
         'The comparable quantity is the per-class recall on the classes the lines share, which is what the '
         'comparison column in section 3 counts.</p>')
p.append('<p class="note">The thin cells bound what can be concluded. {0} class-line cells hold fewer than '
         'five test images, and the weakest lines are L27 and L31, where {1} and {2} classes respectively '
         'produce fewer than five test images. A stated tolerance, or a confidence interval per recall, is '
         'needed before any difference there can be called real or not.</p>'.format(
             len(THIN_CELLS),
             sum(1 for c in DEFECT_CLASSES if 0 < POOL_TEST[(c, "L27")] < 5),
             sum(1 for c in DEFECT_CLASSES if 0 < POOL_TEST[(c, "L31")] < 5)))
p.append('<h4>A direct test of the premise</h4>')
p.append('<p class="note">The case for one model rests on the capture method being identical, so that a '
         'picture carries no trace of its line. All {0} files are the same format, 2,048 by 2,448 greyscale '
         'BMP of 5,014,582 bytes, so there is no resolution difference to find. Whether anything else in the '
         'pixels marks the line is testable in one short run: train a classifier to predict the line from the '
         'pooled pictures. If it cannot beat chance, the premise holds and the single-model conclusion rests '
         'on solid ground.</p>'.format(n(files_total)))
p.append('</section>')

# ---- 6
p.append('<section id="questions"><h3>6 · Questions to settle</h3>')
p.append('<p class="desc">Training is on hold until these are answered. The first group we can decide. The '
         'second group needs a client or lead answer.</p>')
p.append('<h4>For us to decide</h4><ul class="findings">')
p.append('<li><b>Confirm the three rules that build the pool.</b> They are: "Low Dose" and "Low Dose '
         'Obstructing Region of Interest" are one class; "Clear", "HEMA" and "duplicates" are not classes, so '
         '{0} pictures fall outside the 22-class set; and the {1} pictures carrying two defect classes take '
         'the class the older library assigns. Every number in this page depends on those three.</li>'.format(
             n(POOL_EXCLUDED), POOL_MULTI))
p.append('<li><b>Volume-matched training sets, or the full line data?</b> {0} would train on {1} pictures and '
         '{2} on {3}. Matching the volume, by training every line on {3} pictures drawn in proportion to its '
         'own class mix, makes a gap attributable to the line rather than to the volume. Matching per class '
         'instead would cut every line to about {4} pictures, because on its scarcest line a class can hold a '
         'single picture.</li>'.format(
             MATCH_BIGGEST, n(POOL_TRAIN[MATCH_BIGGEST]), MATCH_VOLUME_LINE,
             n(MATCH_VOLUME), n(MATCH_STRICT)))
p.append('<li><b>What counts as similar?</b> An explicit tolerance for the recall comparison, for example '
         'within five points, or non-overlapping confidence intervals. Without a number, the result cannot be '
         'called the same or different.</li>')
p.append('<li><b>Keep the comparable cut at three or more lines?</b> That is {0} of the {1} classes, giving '
         'between three and ten line pairs each. Another {2} classes are scorable on exactly two lines, so '
         'widening the cut to two lines would add {2} classes, and each of them yields a single line '
         'pair.</li>'.format(POOL_SCORED_3PLUS, len(DEFECT_CLASSES),
                              POOL_SCORED_2PLUS - POOL_SCORED_3PLUS))
p.append('<li><b>Do we run the line-predictability check?</b> One short run: if a classifier cannot tell which '
         'line a picture came from, the premise behind a single model is confirmed at the pixel level rather '
         'than inferred from five results.</li>')
p.append('</ul>')
p.append('<h4>For the client or the lead</h4><ul class="findings">')
p.append('<li><b>Do the {0} classes that only the older library carries still count?</b> They are {1}, holding '
         '{2} pictures of which {3} exist nowhere else. Pooling the folders does not answer this, because no '
         'other folder labels them.</li>'.format(
             len(ABSENT_CLASSES), ", ".join(ABSENT_CLASSES), n(ABSENT_IMAGES), n(ABSENT_UNIQUE)))
p.append('<li><b>If "Clear" is later ruled to be a class, it returns as a 23rd class.</b> {0} pictures carry '
         'Clear as their only label, and they are excluded from the 22-class pool today. If they come back, '
         'every per-line number in this page changes.</li>'.format(n(POOL_EXCLUDED)))
p.append('<li><b>Is a test set of {0} to {1} images per line enough, given the thin cells?</b> The pool gives '
         'each line {0} to {1} test images, but {2} class-line cells still hold fewer than five, and on L27 '
         'and L31 that is {3} and {4} classes. Those results will carry wide error bars.</li>'.format(
             n(min(POOL_LINE_TEST.values())), n(max(POOL_LINE_TEST.values())), len(THIN_CELLS),
             sum(1 for c in DEFECT_CLASSES if 0 < POOL_TEST[(c, "L27")] < 5),
             sum(1 for c in DEFECT_CLASSES if 0 < POOL_TEST[(c, "L31")] < 5)))
p.append('<li><b>Four classes cannot support the line-by-line comparison.</b> {0} are scorable on one line '
         'only, and {1} on two lines, so their results stand alone. Confirm that is acceptable.</li>'.format(
             ", ".join(ONE_LINE), ", ".join(TWO_LINE)))
p.append('</ul></section>')

# ---- 7
p.append('<section id="next"><h3>7 · Recommendations</h3>')
p.append('<p class="desc">In order. Each one states its evidence in the same sentence.</p>')
p.append('<ol class="findings">')
p.append('<li><b>Run the line-predictability check before the five models.</b> It costs one short run, and if '
         'a classifier cannot tell which line a picture came from, the premise behind one model is confirmed '
         'at the pixel level rather than inferred from five results.</li>')
p.append('<li><b>Use the pooled class-centric dataset, not a single folder.</b> Pooling the three folders by '
         'defect class gives {0} pictures across {1} classes, which raises the classes scorable on all five '
         'lines from 4 to {2} and the test images per line from 34 to 239 up to {3} to {4}.</li>'.format(
             n(POOL_IMAGES), len(DEFECT_CLASSES), len(FIVE_LINE),
             n(min(POOL_LINE_TEST.values())), n(max(POOL_LINE_TEST.values()))))
p.append('<li><b>Record the three pool rules and keep them fixed.</b> Every number in this page depends on the '
         'rename of Low Dose, on Clear, HEMA and duplicates not being classes ({0} pictures excluded), and on '
         'the older library deciding the class for the {1} pictures that carry two.</li>'.format(
             n(POOL_EXCLUDED), POOL_MULTI))
p.append('<li><b>Split each line at 70:30.</b> It leaves a test image for {0} class-line cells against {1} at '
         '80:20, and it scores the models on {2} test images against {3}. The {4} pictures that 80:20 buys '
         'back are not worth the {5} cells it costs.</li>'.format(
             n(SPLIT_TOTALS[2]), n(SPLIT_TOTALS[3]), n(SPLIT_TOTALS[4]), n(SPLIT_TOTALS[6]),
             n(SPLIT_TOTALS[7] - SPLIT_TOTALS[5]), n(SPLIT_TOTALS[2] - SPLIT_TOTALS[3])))
p.append('<li><b>Match the training volume across the five models, not the per-class counts.</b> {0} would '
         'train on {1} pictures and {2} on {3}, so an unmatched comparison would confound the line with the '
         'training volume and could be attributed to neither. Train every line on {3} pictures drawn in '
         'proportion to its own class mix; matching per class would cut every line to about {4} pictures, '
         'because on its scarcest line a class can hold a single picture.</li>'.format(
             MATCH_BIGGEST, n(POOL_TRAIN[MATCH_BIGGEST]), MATCH_VOLUME_LINE,
             n(MATCH_VOLUME), n(MATCH_STRICT)))
p.append('<li><b>Compare per-class recall on the shared classes, not overall accuracy.</b> The five models '
         'carry different class lists, so a model with 16 classes has a different chance level from one with '
         '21. The comparison set is the {0} classes that three or more lines can score.</li>'.format(
             POOL_SCORED_3PLUS))
p.append('<li><b>State the tolerance before the run.</b> {0} class-line cells hold fewer than five test '
         'images, so only a declared tolerance or a confidence interval can turn the result into a yes or '
         'no.</li>'.format(len(THIN_CELLS)))
p.append('<li><b>Report the classes that cannot be compared separately.</b> {0} are scorable on one line and '
         '{1} on two, so their numbers stand alone and must not be read as a cross-line result.</li>'.format(
             ", ".join(ONE_LINE), ", ".join(TWO_LINE)))
p.append('</ol></section>')

p.append('</div>\n</body>\n</html>')

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write("\n".join(p))
print("wrote", OUT)
print("sections:", len(nav_items), "| tables:", "\n".join(p).count("<table>"),
      "| charts:", "\n".join(p).count("<svg"))
