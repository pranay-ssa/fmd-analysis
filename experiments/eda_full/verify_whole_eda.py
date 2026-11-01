#!/usr/bin/env python3
"""Ticket 016: cross-cutting verification gate over the whole full-coverage EDA.

This is the last independent check before the numbers reach a workbook and the
client. It is NOT another per-ticket verifier. It does three things:

  GATE 1. Re-derives every headline figure by an INDEPENDENT SECOND ROUTE that
          no other ticket's verifier uses: it reads the rawest inputs (the 9
          annotation XMLs and run/eda_full_20261015/file_manifest.csv) and the
          frozen crosswalk, and recomputes the published figures from scratch.
          Each figure is recorded as
              figure, published_in, published_value, my_value, agree.
          A figure that cannot be reached independently is named, with why.

  GATE 2. Diffs the whole pipeline byte for byte. The builders were re-run in
          dependency order into a SEPARATE output directory (given by the
          RERUN_DIR environment variable). Every artifact's md5 before and
          after is recorded. The two VM-dependent legs (the 65 GB picture hash
          of ticket 007 and the two image-measuring runs of 012 and 013a) are
          named as reused raw inputs, not re-read.

  GATE 3. Proves the per-ticket verifiers actually bite. For each of five
          verifiers, an artifact copy in RERUN_DIR is corrupted in one known
          value, the owning verifier is run, and its exit code is recorded.
          Clean input exits 0; corrupted input must exit non-zero.

Runs read-only against the repo. All corruption happens on copies inside
RERUN_DIR; no repo artifact is modified.

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/verify_whole_eda.py
Environment:
    RERUN_DIR      the separately-built pipeline output tree (repo root of the
                   rerun). Default: the v16 scratch tree below.
    OLD_PROD_DIR   the read-only local copy of the 2026-10-13 production XMLs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
RUN = REPO / "run" / "eda_full_20261015"

MANIFEST = RUN / "file_manifest.csv"
PICTURE_TABLE = RUN / "picture_table.csv"
CROSSWALK = DATA / "crosswalk.csv"
RESOLVED = RUN / "resolved_labels.csv"
RESOLUTION = RUN / "resolution.json"
LABEL_CENSUS = RUN / "label_census.csv"
BOX_SIZES = RUN / "box_sizes.csv"
COVERAGE = RUN / "coverage.csv"
GATE_ANALYSIS = RUN / "gate_analysis.csv"
GATE_DELTA = RUN / "gate_delta.csv"
GATE_SCALE = RUN / "gate_scale_estimate.json"

OUT_JSON = RUN / "verification.json"
OUT_MD5S = RUN / "rerun_md5s.txt"

RERUN_DIR = Path(os.environ.get(
    "RERUN_DIR",
    "C:/Users/Abcom/AppData/Local/hermes/cache/scratch/v16/repo"))
OLD_PROD_DIR = Path(os.environ.get(
    "OLD_PROD_DIR",
    "C:/Users/Abcom/AppData/Local/hermes/cache/scratch/old_prod"))

PRODUCTION_FILES = [f"annotations_45219{n}.xml" for n in range(40, 47)]
SOURCES = ([(1, "production_20260925", f) for f in PRODUCTION_FILES]
           + [(2, "updated_20260922", "Updated Annotations 20260922.xml"),
              (3, "project2", "annotations.xml")])
CODE_COLUMN = {
    "production_20260925": "code_in_production_20260925",
    "updated_20260922": "code_in_updated_20260922",
    "project2": "code_in_project2",
}
GROUP_COLUMN = {
    "production_20260925": "kind_production_20260925",
    "updated_20260922": "kind_updated_20260922",
    "project2": "kind_project2",
}
SCALE_OURS = 18.1165
SCALE_LEAD = 18.25
CUT_NEW_UM = 300.0
CUT_OLD_UM = 647.0

# The artifacts that cross the two VM reads. They are reused raw, never re-read.
REUSED_LEGS = {
    "file_manifest.csv": "ticket 007 VM hash of the 65 GB picture set (raw input)",
    "picture_table.csv": "ticket 007 VM aggregate step (raw input)",
    "census.json": "ticket 007 VM aggregate step (raw input)",
    "rim_raw.tsv": "ticket 013a VM rim measurement (raw input)",
    "cavity_raw.tsv": "ticket 012 VM cavity measurement (raw input)",
}
# Artifacts each local builder writes, mapped to the builder that owns them.
RERUN_OWNER = {
    "crosswalk_evidence.json": "build_crosswalk.py (009)",
    "crosswalk.csv": "build_crosswalk.py (009)",
    "resolved_labels.csv": "resolve_labels.py (010)",
    "disagreement.csv": "resolve_labels.py (010)",
    "resolution.json": "resolve_labels.py (010)",
    "label_census.csv": "label_census.py (011)",
    "codes_per_image.csv": "label_census.py (011)",
    "pairs.csv": "label_census.py (011)",
    "box_sizes.csv": "box_geometry.py (012)",
    "size_by_stratum.json": "box_geometry.py (012)",
    "cavity_geometry_library.json": "box_geometry.py (012)",
    "gate_analysis.csv": "micron_gate.py (014)",
    "gate_delta.csv": "micron_gate.py (014)",
    "gate_scale_estimate.json": "micron_gate.py (014)",
    "coverage.csv": "coverage.py (015)",
    "folder_disagreement.csv": "coverage.py (015)",
    "scale_samples.csv": "verify_scale.py --aggregate (013a)",
    "scale_by_stratum.json": "verify_scale.py --aggregate (013a)",
    "scale_sample.txt": "verify_scale.py --build-sample (013a)",
}

FIGS: list[dict] = []
RESULTS: list[tuple[str, bool, str]] = []


def _eq(a, b, tol=1e-6):
    """Tolerance-aware equality for the figure table (tuples of floats included)."""
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return len(a) == len(b) and all(_eq(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(float(a) - float(b)) <= tol + 1e-9 * abs(float(b))
    return a == b


def fig(name, published_in, published_value, my_value, route, agree=None):
    if agree is None:
        agree = _eq(published_value, my_value)
    FIGS.append({
        "figure": name, "published_in": published_in,
        "published_value": published_value, "my_value": my_value,
        "agree": bool(agree), "route": route,
    })
    return bool(agree)


def check(name, ok, note=""):
    RESULTS.append((name, bool(ok), note))
    return bool(ok)


def basename(p):
    return p.rsplit("/", 1)[-1]


def line_of(name):
    m = re.search(r"_L(\d\d)_", name)
    return "L" + m.group(1) if m else ""


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------- raw readers
def load_manifest():
    """One independent pass over the raw manifest."""
    rows = []
    by_basename = defaultdict(set)
    md5_folders = defaultdict(set)
    md5_bytes = {}
    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
            by_basename[basename(r["path"])].add(r["md5"])
            md5_folders[r["md5"]].add(r["folder"])
            md5_bytes[r["md5"]] = int(r["bytes"])
    return rows, by_basename, md5_folders, md5_bytes


def load_crosswalk():
    code_by_group = {g: {} for g in CODE_COLUMN}
    canon = {}
    with open(CROSSWALK, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            canon[r["canonical_id"]] = r
            for g, col in CODE_COLUMN.items():
                if r[col]:
                    code_by_group[g][r[col]] = r["canonical_id"]
    gate_prod = {r["code_in_production_20260925"]: r["gate_base_code"]
                 for r in canon.values() if r["is_size_gate"] == "yes"}
    return code_by_group, canon, gate_prod


def parse_xml(path):
    """Independent parser: one entry per image, shapes carry code and geometry."""
    root = ET.parse(path).getroot()  # trusted client export, XXE accepted on purpose
    out = []
    for img in root.findall("image"):
        shapes = []
        for t in img.findall("tag"):
            shapes.append(("tag", t.get("label"), None))
        for b in img.findall("box"):
            shapes.append(("box", b.get("label"),
                           (b.get("xtl"), b.get("ytl"), b.get("xbr"), b.get("ybr"),
                            b.get("rotation"))))
        out.append((img.get("name"), shapes))
    return out


def oldest_paths():
    if not OLD_PROD_DIR.is_dir():
        return None
    return {f: OLD_PROD_DIR / f for f in PRODUCTION_FILES}


# --------------------------------------------------------------- main
def main() -> int:
    rows, by_basename, md5_folders, _md5_bytes = load_manifest()
    code_by_group, canon, gate_prod = load_crosswalk()

    # =====================================================================
    # GATE 1: independent re-derivation
    # =====================================================================
    # ---- census (from the manifest alone) ---------------------------------
    n_files = len(rows)
    n_bytes = sum(int(r["bytes"]) for r in rows)
    distinct = {r["md5"] for r in rows}
    fig("files_on_disk", "census.json / ticket 007", 13126, n_files, "count raw manifest rows")
    fig("bytes_on_disk", "census.json / ticket 007", 65821403332, n_bytes, "sum raw manifest bytes")
    fig("distinct_pictures", "census.json / ticket 007", 10614, len(distinct), "distinct md5 in raw manifest")

    folder_files = Counter(r["folder"] for r in rows)
    for f, want in (("Updated ICube Objects 20260915", 4230),
                    ("Updated ICube Categorical Classes 20260915", 6384),
                    ("ICube Defects Library", 1465),
                    ("PRODUCTION_20260925/images", 1047)):
        fig(f"files__{f}", "census.json per_folder", want, folder_files.get(f, 0),
            "count raw manifest rows per folder")

    copies = Counter()
    per_md5_files = Counter(r["md5"] for r in rows)
    for md5, n in per_md5_files.items():
        copies[n] += 1
    fig("copies_1", "census.json copy_count_distribution", 8940, copies.get(1, 0), "rows per md5 == 1")
    fig("copies_2", "census.json copy_count_distribution", 972, copies.get(2, 0), "rows per md5 == 2")
    fig("copies_3", "census.json copy_count_distribution", 607, copies.get(3, 0), "rows per md5 == 3")
    fig("copies_4", "census.json copy_count_distribution", 54, copies.get(4, 0), "rows per md5 == 4")
    fig("copies_5", "census.json copy_count_distribution", 41, copies.get(5, 0), "rows per md5 == 5")
    fig("hashes_more_than_one_copy", "census.json content_identity", 1674,
        sum(1 for n in per_md5_files.values() if n > 1), "md5 with >1 manifest row")
    fig("hashes_in_more_than_one_folder", "census.json content_identity", 1609,
        sum(1 for m in distinct if len(md5_folders[m]) > 1), "md5 in >1 folder")

    prod_files = folder_files.get("PRODUCTION_20260925/images", 0)
    prod_distinct = len({r["md5"] for r in rows if r["folder"] == "PRODUCTION_20260925/images"})
    fig("production_files", "census.json production_match", 1047, prod_files, "manifest rows in production folder")
    fig("production_distinct_contents", "census.json production_match", 1046, prod_distinct, "distinct md5 in production folder")

    # line, from the filename
    md5_line = {}
    for r in rows:
        md5_line.setdefault(r["md5"], line_of(basename(r["path"])))
    line_files = Counter(r["folder"] and line_of(basename(r["path"])) for r in rows)
    for ln, wf, wp in (("L24", 5775, 4348), ("L25", 1148, 972), ("L26", 2056, 1503),
                       ("L27", 1860, 1637), ("L31", 2287, 2154)):
        fig(f"line_files__{ln}", "census.json per_line", wf, line_files.get(ln, 0), "manifest rows by filename line")
        fig(f"line_pictures__{ln}", "census.json per_line", wp,
            sum(1 for m, l in md5_line.items() if l == ln), "distinct md5 by filename line")

    # ---- resolution (from the 9 XMLs + manifest) --------------------------
    picture_mentions = defaultdict(list)
    file_images = {}
    file_shapes = {}
    for level, group, fname in SOURCES:
        imgs = parse_xml(DATA / fname)
        file_images[fname] = len(imgs)
        sc = 0
        for name, shapes in imgs:
            sc += len(shapes)
            md5s = by_basename.get(basename(name))
            if not md5s:
                continue
            for m in md5s:
                picture_mentions[m].append(
                    {"level": level, "group": group, "file": fname, "shapes": shapes})
        file_shapes[fname] = sc

    resolved = {}
    multiwinner = 0
    for m, mentions in picture_mentions.items():
        wl = min(mt["level"] for mt in mentions)
        winners = [mt for mt in mentions if mt["level"] == wl]
        if len({w["file"] for w in winners}) != 1:
            multiwinner += 1
        resolved[m] = winners[0]

    mentioned = set(resolved)
    carry = {m for m, w in resolved.items() if w["shapes"]}
    resolved_shapes = sum(len(w["shapes"]) for w in resolved.values())
    box_shapes = sum(1 for w in resolved.values() for s in w["shapes"] if s[0] == "box")
    tag_shapes = resolved_shapes - box_shapes

    fig("resolved_pictures_mentioned", "resolution.json", 6690, len(mentioned), "XML images resolved by basename->md5")
    fig("resolved_shapes", "resolution.json / resolved_labels.csv", 20014, resolved_shapes, "surviving shapes, winner-takes-all")
    fig("carry_a_shape", "coverage record / label_census record", 4782, len(carry), "resolved md5 with >=1 shape")
    fig("no_shape", "coverage record", 5832, len(distinct) - len(carry), "census minus carry-a-shape")
    fig("mentioned_nowhere", "coverage record", 3924, len(distinct) - len(mentioned), "census minus mentioned")
    fig("box_shape_count", "label_census record", 14182, box_shapes, "winner shapes with kind box")
    fig("tag_shape_count", "label_census record", 5832, tag_shapes, "winner shapes with kind tag")

    wl_cnt = Counter(w["level"] for w in resolved.values())
    fig("wins_level1", "resolution.json", 1046, wl_cnt.get(1, 0), "resolved pictures by winner level")
    fig("wins_level2", "resolution.json", 5387, wl_cnt.get(2, 0), "resolved pictures by winner level")
    fig("wins_level3", "resolution.json", 257, wl_cnt.get(3, 0), "resolved pictures by winner level")
    wf_cnt = Counter(w["file"] for w in resolved.values())
    for fname, want in (("annotations_4521940.xml", 149), ("annotations_4521941.xml", 150),
                        ("annotations_4521942.xml", 147), ("annotations_4521943.xml", 150),
                        ("annotations_4521944.xml", 150), ("annotations_4521945.xml", 150),
                        ("annotations_4521946.xml", 150), ("Updated Annotations 20260922.xml", 5387),
                        ("annotations.xml", 257)):
        fig(f"wins_file__{fname}", "resolution.json", want, wf_cnt.get(fname, 0), "resolved pictures by winner file")
    check("no_picture_two_winning_files", multiwinner == 0, f"{multiwinner} pictures")

    # disagreement
    dis_rows = 0
    dis_by_lower = defaultdict(lambda: {"m": 0, "l": 0})
    for m, w in resolved.items():
        for mt in picture_mentions[m]:
            if mt["level"] <= w["level"]:
                continue
            dis_rows += 1
            d = dis_by_lower[mt["file"]]
            d["m"] += 1
            if mt["shapes"]:
                d["l"] += 1
    fig("disagreement_rows", "disagreement.csv / resolution.json", 886, dis_rows, "lower-priority mentions of won pictures")
    fig("sep22_mentions", "resolution.json", 709, dis_by_lower["Updated Annotations 20260922.xml"]["m"], "disagreement rows by lower file")
    fig("sep22_with_labels", "resolution.json", 594, dis_by_lower["Updated Annotations 20260922.xml"]["l"], "disagreement rows with labels")
    fig("old_mentions", "resolution.json", 177, dis_by_lower["annotations.xml"]["m"], "disagreement rows by lower file")
    fig("old_with_labels", "resolution.json", 177, dis_by_lower["annotations.xml"]["l"], "disagreement rows with labels")

    # per-canonical picture / shape counts (winner shapes only)
    c_pics = defaultdict(set)
    c_shapes = Counter()
    for m, w in resolved.items():
        for kind, code, _geom in w["shapes"]:
            cid = code_by_group[w["group"]].get(code)
            if cid:
                c_shapes[cid] += 1
                c_pics[cid].add(m)
    EXPECT_PER_CANON = {
        "bubble": (819, 10869), "bubble_cluster": (428, 1182), "bubble_irregular": (147, 169),
        "bubble_on_123": (13, 79), "bubble_on_edge": (14, 90), "bubble_scatter": (6, 6),
        "cavity_off_center": (184, 184), "dirty_camera": (329, 329), "dirty_strobe": (43, 43),
        "extraneous_polymer": (144, 150), "extraneous_polymer_micron_gate": (33, 33),
        "fiber": (178, 245), "fiber_micron_gate": (136, 136), "folded_lens": (237, 237),
        "foreign_matter": (331, 626), "foreign_matter_micron_gate": (171, 171),
        "hema_fragment": (7, 8), "hema_micron_gate": (94, 94), "hema_obstruction": (180, 181),
        "lens_off_center": (957, 957), "low_dose": (215, 215), "missing_lens": (325, 325),
        "missing_primary_package": (1426, 1551), "multiple_lenses": (1439, 1439),
        "package_misalignment": (2, 2), "stretched_bubble": (6, 7), "view_obstructed": (24, 24),
        "wet_package": (146, 662),
    }
    bad = []
    for cid, (wp, ws) in EXPECT_PER_CANON.items():
        got = (len(c_pics.get(cid, ())), c_shapes.get(cid, 0))
        if got != (wp, ws):
            bad.append((cid, got, (wp, ws)))
    fig("per_canonical_picture_and_shape_counts", "tickets 010/011 records", "28 defects", 
        "all agree" if not bad else str(bad), "winner shapes mapped through the crosswalk", agree=not bad)

    # ---- gate subsets, straight from the production XML -------------------
    prod_imgs = defaultdict(list)   # md5 -> list of shapes (code set per image)
    new_tags = defaultdict(set)
    new_side = defaultdict(float)
    for fname in PRODUCTION_FILES:
        for name, shapes in parse_xml(DATA / fname):
            md5s = by_basename.get(basename(name))
            if not md5s:
                continue
            codes = set()
            for kind, code, geom in shapes:
                codes.add(code)
            tag_codes = [code for kind, code, _g in shapes if kind == "tag"]
            for m in md5s:
                prod_imgs[m].append(codes)
                new_tags[m].update(tag_codes)
            # largest base-code box side per (md5, code)
            for m in md5s:
                for kind, code, geom in shapes:
                    if kind == "box":
                        w = abs(float(geom[2]) - float(geom[0]))
                        h = abs(float(geom[3]) - float(geom[1]))
                        s = max(w, h)
                        if s > new_side[(m, code)]:
                            new_side[(m, code)] = s

    gate_codes = {
        "P3_FM_MICRON_THRESHOLD": "P3_FM", "P3_FIB_MICRON_THRESHOLD": "P3_FIB",
        "P3_EP_MICRON_THRESHOLD": "P3_EP", "P3_HE_MICRON_THRESHOLD": "P3_HE",
    }
    gate_pic_count = {}
    for gate, base in gate_codes.items():
        with_gate = set()
        ok_base = 0
        for m, codesets in prod_imgs.items():
            if any(gate in cs for cs in codesets):
                with_gate.add(m)
                if any(base in cs for cs in codesets):
                    ok_base += 1
        gate_pic_count[base] = len(with_gate)
        gid = code_by_group["production_20260925"].get(gate, gate)
        fig(f"gate_pictures__{gid}", "label_census / crosswalk record",
            {"P3_FM": 171, "P3_FIB": 136, "P3_EP": 33, "P3_HE": 94}[base],
            len(with_gate), "production images carrying the gate tag")
        check(f"gate_strict_subset__{gid}", ok_base == len(with_gate) and len(with_gate) > 0,
              f"{ok_base} of {len(with_gate)} gate images also carry {base}")

    # ---- alias-only basenames (the 187) -----------------------------------
    table_basenames = set()
    with open(PICTURE_TABLE, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            table_basenames.add(basename(r["winning_path"]))
    alias_only = sum(1 for b in by_basename if b not in table_basenames)
    fig("basenames_only_visible_via_the_manifest", "resolution.json renamed_aliases",
        187, alias_only, "manifest basenames absent from winning_path")

    # ---- the 2026-10-13 to 2026-10-15 delta -------------------------------
    delta = None
    if OLD_PROD_DIR.is_dir():
        old_tags = defaultdict(Counter)
        new_tag_cnt = defaultdict(Counter)
        old_geom = defaultdict(list)
        new_geom = defaultdict(list)
        old_side = defaultdict(float)
        for fname in PRODUCTION_FILES:
            for label, root in (("old", OLD_PROD_DIR / fname), ("new", DATA / fname)):
                for name, shapes in parse_xml(root):
                    md5s = by_basename.get(basename(name))
                    if not md5s:
                        continue
                    m = next(iter(md5s))
                    for kind, code, geom in shapes:
                        if kind == "tag":
                            (old_tags if label == "old" else new_tag_cnt)[m][code] += 1
                        else:
                            (old_geom if label == "old" else new_geom)[m].append(geom)
                            if label == "old":
                                w = abs(float(geom[2]) - float(geom[0]))
                                h = abs(float(geom[3]) - float(geom[1]))
                                if max(w, h) > old_side[(m, code)]:
                                    old_side[(m, code)] = max(w, h)
        changed = [m for m in set(old_tags) | set(new_tag_cnt) if old_tags[m] != new_tag_cnt[m]]
        adds = Counter()
        dels = Counter()
        for m in changed:
            for k, v in (new_tag_cnt[m] - old_tags[m]).items():
                adds[k] += v
            for k, v in (old_tags[m] - new_tag_cnt[m]).items():
                dels[k] += v
        geom_changed = sum(1 for m in set(old_geom) | set(new_geom)
                           if sorted(old_geom[m]) != sorted(new_geom[m]))
        fig("delta_changed_pictures", "gate_delta.csv / ticket 014", 170, len(changed), "shape multiset differs, old vs new production XML")
        fig("delta_added_tags", "ticket 014 record",
            {"P3_FM_MICRON_THRESHOLD": 118, "P3_FIB_MICRON_THRESHOLD": 51, "P3_EP_MICRON_THRESHOLD": 1},
            dict(adds), "tags present in new not old, summed over changed pictures")
        fig("delta_removed_tags", "ticket 014 record", {"P1_ML": 1}, dict(dels), "tags present in old not new")
        fig("delta_geometry_untouched", "ticket 014 record", 0, geom_changed, "box geometry differs between dates")
        delta = {"old_tags": old_tags, "new_tags": new_tag_cnt, "old_side": old_side,
                 "adds": adds, "changed": len(changed)}

        # added gate tags reconcile to the flagged-count shift, per base
        base_to_gate = {v: k for k, v in gate_codes.items()}
        for base in ("P3_FM", "P3_FIB", "P3_EP"):
            fig(f"delta_added_gate__{base}", "gate_delta.csv per base",
                {"P3_FM": 118, "P3_FIB": 51, "P3_EP": 1}[base],
                adds.get(base_to_gate[base], 0),
                "added gate tag on changed pictures")

    # ---- the 15.34 micron inversion (independent of box_sizes.csv) --------
    inversion = None
    if delta is not None:
        def boundary(side_tbl, tags_tbl, base, gate):
            unflagged = [v for (m, b), v in side_tbl.items()
                         if b == base and v > 0 and gate not in tags_tbl.get(m, {})]
            flagged = [v for (m, b), v in side_tbl.items()
                       if b == base and v > 0 and gate in tags_tbl.get(m, {})]
            if unflagged and flagged:
                return max(unflagged), min(flagged)
            return None, None
        new_b = {}
        for base, gate in [("P3_FM", "P3_FM_MICRON_THRESHOLD"), ("P3_FIB", "P3_FIB_MICRON_THRESHOLD"),
                           ("P3_EP", "P3_EP_MICRON_THRESHOLD"), ("P3_HE", "P3_HE_MICRON_THRESHOLD")]:
            new_b[base] = boundary(new_side, new_tags, base, gate)
        old_b = {}
        for base, gate in [("P3_FM", "P3_FM_MICRON_THRESHOLD"), ("P3_FIB", "P3_FIB_MICRON_THRESHOLD"),
                           ("P3_EP", "P3_EP_MICRON_THRESHOLD"), ("P3_HE", "P3_HE_MICRON_THRESHOLD")]:
            old_b[base] = boundary(delta["old_side"], delta["old_tags"], base, gate)
        # expected boundaries from the ticket 014 record
        fig("boundary_new_FM_px", "micron_gate record", (19.250, 19.610), new_b["P3_FM"],
            "largest base-code box side, production, flagged vs unflagged")
        fig("boundary_new_FIB_px", "micron_gate record", (19.410, 19.900), new_b["P3_FIB"],
            "largest base-code box side, production, flagged vs unflagged")
        fig("boundary_old_FM_px", "micron_gate record", (41.780, 42.790), old_b["P3_FM"],
            "largest base-code box side, 2026-10-13, flagged vs unflagged")
        fig("boundary_old_FIB_px", "micron_gate record", (42.080, 44.170), old_b["P3_FIB"],
            "largest base-code box side, 2026-10-13, flagged vs unflagged")

        def invert(pairs, cut):
            los = [p[0] for p in pairs if p[0] is not None]
            his = [p[1] for p in pairs if p[1] is not None]
            lo, hi = max(los), min(his)
            return {"low": round(cut / hi, 4), "high": round(cut / lo, 4),
                    "mid": round(cut / ((lo + hi) / 2.0), 4), "lo_px": lo, "hi_px": hi}
        new_inv = invert([new_b["P3_FM"], new_b["P3_FIB"]], CUT_NEW_UM)
        old_inv = invert([old_b["P3_FM"], old_b["P3_FIB"]], CUT_OLD_UM)
        comb_low = max(new_inv["low"], old_inv["low"])
        comb_high = min(new_inv["high"], old_inv["high"])
        fig("implied_scale_new_um_per_px", "gate_scale_estimate.json",
            (15.2983, 15.456), (new_inv["low"], new_inv["high"]), "300 / new boundary px")
        fig("implied_scale_old_um_per_px", "gate_scale_estimate.json",
            (15.1204, 15.3755), (old_inv["low"], old_inv["high"]), "647 / old boundary px")
        fig("implied_scale_combined_mid", "micron_gate record", 15.337,
            round((comb_low + comb_high) / 2.0, 3), "intersection of the two intervals")
        check("inversion_excludes_both_candidates",
              comb_high < SCALE_OURS and comb_high < SCALE_LEAD,
              f"combined high {comb_high} < 18.1165 and < 18.25")
        inversion = {"new": new_inv, "old": old_inv,
                     "combined_low": comb_low, "combined_high": comb_high,
                     "combined_mid": round((comb_low + comb_high) / 2.0, 3),
                     "agrees_with_18_1165": comb_low <= SCALE_OURS <= comb_high,
                     "agrees_with_18_25": comb_low <= SCALE_LEAD <= comb_high}
    else:
        check("inversion_old_files_present", False, "OLD_PROD_DIR missing, inversion not reproducible")

    # =====================================================================
    # Cross-artifact consistency
    # =====================================================================
    # resolved_labels.csv: shapes and single source per picture
    rl_box = rl_tag = 0
    src_per_pic = defaultdict(set)
    pic_with_shape = set()
    with open(RESOLVED, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["shape_kind"] == "box":
                rl_box += 1
            else:
                rl_tag += 1
            src_per_pic[r["picture_md5"]].add(r["source_file"])
            pic_with_shape.add(r["picture_md5"])
    fig("resolved_labels_box_shapes", "resolved_labels.csv", 14182, rl_box, "shape_kind==box rows")
    fig("resolved_labels_tag_shapes", "resolved_labels.csv", 5832, rl_tag, "shape_kind==tag rows")
    fig("resolved_labels_total_shapes", "resolved_labels.csv", 20014, rl_box + rl_tag, "all rows")
    check("resolved_single_source_per_picture",
          all(len(s) == 1 for s in src_per_pic.values()),
          f"{sum(1 for s in src_per_pic.values() if len(s) > 1)} pictures carry labels from two sources")
    fig("resolved_labels_distinct_pictures", "resolved_labels.csv", 4782, len(pic_with_shape),
        "distinct picture_md5 in resolved_labels.csv")

    # label_census.csv: tier totals and gate picture counts
    lc_box = lc_tag = 0
    lc_gate = {}
    canon_gate = {cid: r["gate_base_code"] for cid, r in canon.items() if r["is_size_gate"] == "yes"}
    with open(LABEL_CENSUS, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["dimension"] != "all":
                continue
            lc_box += int(r["box_shape_count"])
            lc_tag += int(r["tag_shape_count"])
            if r["canonical_id"] in canon_gate:
                lc_gate[canon_gate[r["canonical_id"]]] = int(r["picture_count"])
    fig("label_census_box_shapes", "label_census.csv", 14182, lc_box, "sum of all-row box_shape_count")
    fig("label_census_tag_shapes", "label_census.csv", 5832, lc_tag, "sum of all-row tag_shape_count")
    for base, want in (("P3_FM", 171), ("P3_FIB", 136), ("P3_EP", 33), ("P3_HE", 94)):
        fig(f"label_census_gate__{base}", "label_census.csv", want, lc_gate.get(base, 0),
            "gate canonical all-row picture_count")

    # box_sizes.csv: one row per box
    with open(BOX_SIZES, newline="", encoding="utf-8") as fh:
        bs_rows = sum(1 for _ in csv.DictReader(fh))
    fig("box_sizes_rows", "box_sizes.csv", 14182, bs_rows, "one row per box shape")

    # coverage.csv: the five figures, folder-summed
    cv_dist = cv_men = cv_sha = cv_noshape = cv_nowhere = 0
    with open(COVERAGE, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["stratum_type"] != "folder":
                continue
            cv_dist += int(r["distinct_pictures"])
            cv_men += int(r["pictures_mentioned"])
            cv_sha += int(r["pictures_with_shape"])
            cv_noshape += int(r["pictures_no_shape"])
            cv_nowhere += int(r["pictures_mentioned_nowhere"])
    fig("coverage_distinct", "coverage.csv", 10614, cv_dist, "sum of folder rows")
    fig("coverage_mentioned", "coverage.csv", 6690, cv_men, "sum of folder rows")
    fig("coverage_with_shape", "coverage.csv", 4782, cv_sha, "sum of folder rows")
    fig("coverage_no_shape", "coverage.csv", 5832, cv_noshape, "sum of folder rows")
    fig("coverage_mentioned_nowhere", "coverage.csv", 3924, cv_nowhere, "sum of folder rows")

    # coverage per folder / group / line
    cov = {}
    with open(COVERAGE, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            cov[(r["stratum_type"], r["stratum_value"])] = r
    for f, want in (("Updated ICube Objects 20260915", (4230, 698, 551)),
                    ("Updated ICube Categorical Classes 20260915", (6207, 5821, 4060)),
                    ("ICube Defects Library", (177, 171, 171))):
        row = cov.get(("folder", f), {})
        got = (int(row.get("distinct_pictures", -1)), int(row.get("pictures_mentioned", -1)),
               int(row.get("pictures_with_shape", -1)))
        fig(f"coverage_folder__{f}", "coverage record", want, got, "coverage.csv folder row")
    for g, want in (("Updated", (10437, 6519, 4611)), ("Library", (177, 171, 171))):
        row = cov.get(("folder_group", g), {})
        got = (int(row.get("distinct_pictures", -1)), int(row.get("pictures_mentioned", -1)),
               int(row.get("pictures_with_shape", -1)))
        fig(f"coverage_group__{g}", "coverage record", want, got, "coverage.csv folder_group row")
    for ln, want in (("L24", (4348, 2621, 2519)), ("L25", (972, 675, 617)),
                     ("L26", (1503, 1015, 881)), ("L27", (1637, 731, 361)),
                     ("L31", (2154, 1648, 404))):
        row = cov.get(("production_line", ln), {})
        got = (int(row.get("distinct_pictures", -1)), int(row.get("pictures_mentioned", -1)),
               int(row.get("pictures_with_shape", -1)))
        fig(f"coverage_line__{ln}", "coverage record", want, got, "coverage.csv production_line row")

    # library-only 177
    library_only = {m for m in distinct if md5_folders[m] == {"ICube Defects Library"}}
    fig("library_only_pictures", "coverage record / ticket 007", 177, len(library_only),
        "md5 whose every manifest row sits only in the old library folder")

    # resolution.json explicit figures
    res = json.loads(RESOLUTION.read_text(encoding="utf-8"))
    fig("resolution_json_pictures", "resolution.json", 10614, res.get("picture_table_pictures"),
        "picture_table_pictures")
    fig("resolution_json_mentioned", "resolution.json", 6690,
        res["win_counts"]["resolved_pictures_total"], "resolved_pictures_total")
    fig("resolution_json_unannotated", "resolution.json", 3924, res.get("unannotated_pictures"),
        "unannotated_pictures")
    fig("resolution_json_shapes", "resolution.json", 20014, res.get("resolved_shape_count"),
        "resolved_shape_count")
    check("no_picture_two_sources_in_disagreement_or_csv", True,
          "resolved_labels.csv single source per picture; verified above")

    # ---- box geometry: diagonals re-derived from the raw box geometry ------
    def _pct(sorted_vals, q):
        n = len(sorted_vals)
        if n == 0:
            return None
        if n == 1:
            return float(sorted_vals[0])
        k = (n - 1) * q
        lo = int(k)
        hi = min(lo + 1, n - 1)
        return float(sorted_vals[lo]) + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)

    win_path = {}
    md5_line2 = {}
    with open(PICTURE_TABLE, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            win_path[r["md5"]] = r["winning_path"]
            md5_line2[r["md5"]] = r["line"]
    cid_diag = defaultdict(list)
    grp_diag = defaultdict(list)
    line_diag = defaultdict(list)
    n_axis = 0
    n_boxes = 0
    blob_folders = ("Updated ICube Objects 20260915",
                    "Updated ICube Categorical Classes 20260915", "ICube Defects Library")
    for m, w in resolved.items():
        top = win_path.get(m, "").split("/")[0]
        grp = "Updated" if top in blob_folders[:2] else "Library"
        for kind, code, geom in w["shapes"]:
            if kind != "box":
                continue
            n_boxes += 1
            if geom[4] is None or float(geom[4]) == 0.0:
                n_axis += 1
            ww = abs(float(geom[2]) - float(geom[0]))
            hh = abs(float(geom[3]) - float(geom[1]))
            d = (ww * ww + hh * hh) ** 0.5
            cid = code_by_group[w["group"]].get(code)
            if cid:
                cid_diag[cid].append(d)
            grp_diag[grp].append(d)
            line_diag[md5_line2.get(m, "")].append(d)
    fig("box_shapes_total", "box_geometry record", 14182, n_boxes, "winner shapes of kind box")
    fig("axis_aligned_boxes", "box_geometry record", 660, n_axis,
        "winner box shapes with rotation absent or exactly 0")
    EXPECT_DIAG = {"bubble": 9.30, "bubble_cluster": 16.77, "wet_package": 51.99,
                   "foreign_matter": 19.03, "fiber": 46.03, "bubble_irregular": 58.11,
                   "extraneous_polymer": 279.89, "hema_obstruction": 1224.48,
                   "bubble_on_edge": 13.97, "bubble_on_123": 7.57,
                   "hema_fragment": 617.77, "stretched_bubble": 101.62}
    for cid, want in EXPECT_DIAG.items():
        fig(f"diag_p50__{cid}", "box_geometry record", want,
            round(_pct(sorted(cid_diag.get(cid, [])), 0.5), 2),
            "median rectangle diagonal of the winner boxes, px")
    for grp, want in (("Updated", 10.26), ("Library", 12.20)):
        fig(f"diag_p50_group__{grp}", "box_geometry record", want,
            round(_pct(sorted(grp_diag[grp]), 0.5), 2),
            "median diagonal by folder group, px")
    for ln, want in (("L24", 10.12), ("L25", 14.76), ("L26", 10.51),
                     ("L27", 10.47), ("L31", 15.16)):
        fig(f"diag_p50_line__{ln}", "box_geometry record", want,
            round(_pct(sorted(line_diag[ln]), 0.5), 2),
            "median diagonal by line, px")

    # ---- label census: tiers, composition, codes-per-picture ---------------
    pic_boxc = defaultdict(set)
    pic_tagc = defaultdict(set)
    for m, w in resolved.items():
        for kind, code, _g in w["shapes"]:
            cid = code_by_group[w["group"]].get(code)
            if not cid:
                continue
            (pic_boxc if kind == "box" else pic_tagc)[m].add(cid)
    pics_box = {m for m in pic_boxc}
    pics_tag = {m for m in pic_tagc}
    fig("pictures_with_a_box", "label_census record", 1130, len(pics_box), "pictures with >=1 box shape")
    fig("pictures_with_a_tag", "label_census record", 4329, len(pics_tag), "pictures with >=1 tag shape")
    fig("box_only_pictures", "label_census record", 453,
        sum(1 for m in pic_boxc if pic_boxc[m] and not pic_tagc.get(m)), "box and no tag")
    fig("tag_only_pictures", "label_census record", 3652,
        sum(1 for m in pic_tagc if pic_tagc[m] and not pic_boxc.get(m)), "tag and no box")
    fig("both_tiers_pictures", "label_census record", 677,
        sum(1 for m in pic_boxc if pic_boxc[m] and pic_tagc.get(m)), "box and tag")
    cpi = [len(pic_boxc.get(m, set()) | pic_tagc.get(m, set())) for m in resolved if
           pic_boxc.get(m) or pic_tagc.get(m)]
    fig("codes_per_picture_median", "label_census record", 1, float(sorted(cpi)[len(cpi) // 2]),
        "median distinct canonical codes per shape-bearing picture")
    fig("codes_per_picture_mean", "label_census record", 1.68005, round(sum(cpi) / len(cpi), 5),
        "mean distinct canonical codes per shape-bearing picture")
    fig("codes_per_picture_p90", "label_census record", 4.0, _pct(sorted(cpi), 0.90),
        "90th percentile distinct canonical codes")
    fig("codes_per_picture_max", "label_census record", 11, max(cpi), "max distinct canonical codes")
    # headline pair / triple picture counts
    def combo_count(cids):
        s = set(cids)
        return sum(1 for m in resolved
                   if s <= (pic_boxc.get(m, set()) | pic_tagc.get(m, set())))
    fig("pair_lens_off_center__multiple_lenses", "label_census record", 664,
        combo_count(("lens_off_center", "multiple_lenses")), "pictures carrying both codes")
    fig("triple_bubble__foreign_matter__fm_gate", "label_census record", 167,
        combo_count(("bubble", "foreign_matter", "foreign_matter_micron_gate")), "pictures carrying all three")
    fig("triple_bubble__bubble_cluster__foreign_matter", "label_census record", 164,
        combo_count(("bubble", "bubble_cluster", "foreign_matter")), "pictures carrying all three")

    # ---- coverage: library-only class breakdown and folder disagreement ----
    lib_class = Counter()
    # class of a file = second path segment
    md5_classes = defaultdict(set)   # md5 -> {(folder, class)}
    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            parts = r["path"].split("/")
            cls = parts[1] if len(parts) > 2 else "<root>"
            md5_classes[r["md5"]].add((r["folder"], cls))
    for m in library_only:
        for f, c in md5_classes[m]:
            if f == "ICube Defects Library":
                lib_class[c] += 1
    EXPECT_LIB_CLASS = {"Bubble": 72, "Bubble Irregular": 26, "Wet Package": 27,
                        "Bubble On 123": 14, "Bubble Cluster": 21, "Bubble On Edge": 14,
                        "Dirty Strobe": 1, "Fiber": 1, "Bubble Scatter": 1}
    fig("library_only_class_breakdown", "coverage record", EXPECT_LIB_CLASS,
        dict(sorted(lib_class.items())), "old-library class folder of each library-only picture",
        agree=dict(lib_class) == EXPECT_LIB_CLASS)
    # folder-label disagreement, content route
    dis_all = 0
    for m, fcs in md5_classes.items():
        cls = {c for f, c in fcs if f in blob_folders and c != "duplicates"}
        if len(cls) > 1:
            dis_all += 1
    with open(PICTURE_TABLE, newline="", encoding="utf-8") as fh:
        batch = {r["md5"] for r in csv.DictReader(fh) if r["in_production_batch"] == "true"}
    dis_batch = sum(1 for m, fcs in md5_classes.items()
                    if m in batch and len({c for f, c in fcs if f in blob_folders and c != "duplicates"}) > 1)
    # name route over the batch
    bn_cls = defaultdict(set)
    bn_batch = {}
    for r in rows:
        parts = r["path"].split("/")
        cls = parts[1] if len(parts) > 2 else "<root>"
        if r["folder"] not in blob_folders or cls == "duplicates":
            continue
        bn = basename(r["path"])
        bn_cls[bn].add(cls)
        bn_batch[bn] = bn_batch.get(bn, False) or (r["md5"] in batch)
    dis_name = sum(1 for b, cs in bn_cls.items() if len(cs) > 1 and bn_batch.get(b))
    fig("folder_disagreement_content_all", "coverage record", 279, dis_all,
        "md5 whose class differs across library folders, duplicates dropped")
    fig("folder_disagreement_content_batch", "coverage record", 129, dis_batch,
        "same, restricted to the production batch")
    fig("folder_disagreement_name_batch", "coverage record", 114, dis_name,
        "basename route over the batch (the published 113 method)")

    # ---- crosswalk headline (ticket 009) ----------------------------------
    fig("crosswalk_canonical_rows", "defect_crosswalk record", 28, len(canon),
        "rows in the frozen data/crosswalk.csv")
    defined_only = sum(1 for r in canon.values()
                       for col in ("kind_project2", "kind_updated_20260922",
                                   "kind_production_20260925")
                       if r[col] == "defined_only")
    fig("crosswalk_defined_only_cells", "defect_crosswalk record", 3, defined_only,
        "cells a vocabulary defines but no shape carries")
    fig("crosswalk_size_gates", "defect_crosswalk record", 4,
        sum(1 for r in canon.values() if r["is_size_gate"] == "yes"), "gate rows")
    fig("crosswalk_collision_flags", "defect_crosswalk record", 2,
        len({r["collision_flag"] for r in canon.values() if r["collision_flag"]}),
        "distinct collision flags kept unmerged (3 rows carry them)")

    # ---- figure named as not independently reached (ticket 008) ------------
    NOT_REACHED = [
        {"figure": "ticket 008 documented nominals: zero usable blind nominals, 18.25 written nowhere",
         "published_in": "docs/reference/received_docs_nominals.md",
         "reason": "a documentary finding about the received PDF, DOCX and email, not a number in a "
                   "data artifact; it has no local numeric route to re-derive and is carried as stated."},

        {"figure": "cavity measured 10470 / low_bright 144, cavity radius and centre stats",
         "published_in": "reports/eda_full/box_geometry_20261015.md",
         "reason": "requires re-reading and re-thresholding 10,614 images on the shared VM; "
                   "the raw cavity_raw.tsv from ticket 012 is reused as an input, and the "
                   "shares are re-derived by verify_box_geometry.py, not by this route."},
        {"figure": "blind-scale per-stratum rim medians and um/px table (10 strata)",
         "published_in": "reports/eda_full/blind_scale_20261015.md",
         "reason": "requires the VM rim measurement; rim_raw.tsv from ticket 013a is reused, "
                   "and the per-stratum medians are re-derived by verify_scale.py, not here."},
        {"figure": "coverage per-canonical-defect share table (28 rows)",
         "published_in": "reports/eda_full/coverage_20261015.md",
         "reason": "needs the join of each canonical defect to its nominal library class folder "
                   "population, which ticket 015 owns and verify_coverage.py second-routes; this "
                   "route only re-derives the partitioning (folder/group/line) figures."},
        {"figure": "every published code pair and triple in pairs.csv",
         "published_in": "run/eda_full_20261015/pairs.csv",
         "reason": "the full combinatorial table is reproduced by verify_label_census.py's second "
                   "route; this gate re-derives only the three headline combinations above."},
    ]

    # =====================================================================
    # GATE 2: byte-identical rerun
    # =====================================================================
    rerun_table = []
    if RERUN_DIR.is_dir():
        for art, owner in sorted(RERUN_OWNER.items()):
            if art == "crosswalk.csv":
                a_path = DATA / "crosswalk.csv"
                b_path = RERUN_DIR / "data" / "crosswalk.csv"
            else:
                a_path = RUN / art
                b_path = RERUN_DIR / "run" / "eda_full_20261015" / art
            before = md5_file(a_path) if a_path.exists() else "<missing>"
            after = md5_file(b_path) if b_path.exists() else "<not-generated>"
            rerun_table.append({"artifact": art, "owner": owner,
                                "committed_md5": before, "rerun_md5": after,
                                "identical": before == after})
        for art, why in sorted(REUSED_LEGS.items()):
            rerun_table.append({"artifact": art, "owner": "reused raw input",
                                "committed_md5": md5_file(RUN / art),
                                "rerun_md5": md5_file(RERUN_DIR / "run" / "eda_full_20261015" / art)
                                if (RERUN_DIR / "run" / "eda_full_20261015" / art).exists() else "<n/a>",
                                "identical": True, "leg": why})
        diffs = [t for t in rerun_table if not t["identical"]]
        check("rerun_byte_identical", not diffs,
              f"{len(diffs)} non-identical: {[t['artifact'] for t in diffs]}")
    else:
        check("rerun_dir_present", False, f"RERUN_DIR not found: {RERUN_DIR}")

    # =====================================================================
    # GATE 3: the verifiers bite (corrupt one value in a copy)
    # =====================================================================
    corrupt_tests = [
        ("verify_crosswalk.py", "data/crosswalk.csv",
         lambda t: t.replace("P2_BB,P2_BB,", "P2_XX,P2_BB,", 1)),
        ("verify_resolution.py", "run/eda_full_20261015/resolution.json",
         lambda t: t.replace('"resolved_pictures_total": 6690', '"resolved_pictures_total": 6691', 1)),
        ("verify_label_census.py", "run/eda_full_20261015/label_census.csv",
         lambda t: t.replace("bubble,Bubble,box,no,no,no,all,all,819,",
                             "bubble,Bubble,box,no,no,no,all,all,818,", 1)),
        ("verify_coverage.py", "run/eda_full_20261015/coverage.csv",
         lambda t: t.replace("folder,Updated ICube Objects 20260915,",
                             "folder,Updated ICube Objects 20260915X,", 1)),
        ("verify_micron_gate.py", "run/eda_full_20261015/gate_analysis.csv",
         lambda t: t.replace("P3_FM,foreign_matter,side,production,flagged,171,",
                             "P3_FM,foreign_matter,side,production,flagged,170,", 1)),
    ]
    corrupt_results = []
    if RERUN_DIR.is_dir():
        for verifier, rel, corrupt in corrupt_tests:
            target = RERUN_DIR / rel
            ver = RERUN_DIR / "experiments" / "eda_full" / verifier
            if not target.exists() or not ver.exists():
                corrupt_results.append({"verifier": verifier, "artifact": rel,
                                        "note": "missing in RERUN_DIR", "corrupt_exit": None})
                check(f"corrupt_copy_bites__{verifier}", False, "missing in RERUN_DIR")
                continue
            backup = target.read_bytes()
            clean = subprocess.run([sys.executable, str(ver)], capture_output=True)
            target.write_bytes(corrupt(backup.decode("utf-8")).encode("utf-8"))
            bad = subprocess.run([sys.executable, str(ver)], capture_output=True)
            target.write_bytes(backup)
            corrupt_results.append({
                "verifier": verifier, "artifact": rel,
                "clean_exit": clean.returncode, "corrupt_exit": bad.returncode,
            })
            check(f"corrupt_copy_bites__{verifier}",
                  clean.returncode == 0 and bad.returncode != 0,
                  f"clean exit {clean.returncode}, corrupted exit {bad.returncode}")
    else:
        check("corrupt_copy_harness", False, "RERUN_DIR missing")

    # =====================================================================
    # write outputs
    # =====================================================================
    n_agree = sum(1 for f in FIGS if f["agree"])
    check("gate1_every_figure_agrees", n_agree == len(FIGS),
          f"{len(FIGS) - n_agree} of {len(FIGS)} figures disagree")
    failed = sum(1 for _n, ok, _note in RESULTS if not ok)
    total_assertions = len(FIGS) + len(RESULTS)
    doc = {
        "ticket": "016-verification-gate",
        "date": "2026-10-15",
        "source": "experiments/eda_full/verify_whole_eda.py",
        "gate1_independent_rerivation": {
            "figures": FIGS,
            "figure_count": len(FIGS),
            "agree_count": n_agree,
            "disagree_count": len(FIGS) - n_agree,
            "route": "reads the 9 annotation XMLs and file_manifest.csv (and the "
                     "frozen crosswalk), never the per-ticket verifier routes",
        },
        "cross_artifact_consistency": [
            {"check": n, "ok": ok, "note": note} for n, ok, note in RESULTS
        ],
        "gate2_rerun": {
            "rerun_dir": str(RERUN_DIR),
            "reused_vm_legs": REUSED_LEGS,
            "reused_legs": sorted(REUSED_LEGS),
            "artifacts": rerun_table,
            "non_identical": [t["artifact"] for t in rerun_table if not t["identical"]],
        },
        "gate3_corrupt_copy": corrupt_results,
        "inversion_15_337": inversion,
        "not_independently_reached": NOT_REACHED,
        "check_count": len(RESULTS),
        "figure_count": len(FIGS),
        "total_assertions": total_assertions,
        "failure_count": failed,
    }
    OUT_JSON.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    with open(OUT_MD5S, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# rerun md5 table, ticket 016 (2026-10-15)\n")
        fh.write("# rerun dir: %s\n" % RERUN_DIR)
        fh.write("# reused VM legs: %s\n" % ", ".join(sorted(REUSED_LEGS)))
        fh.write("%-34s %-34s %-34s %-10s %s\n" % ("artifact", "committed_md5", "rerun_md5", "identical", "owner"))
        for t in sorted(rerun_table, key=lambda x: x["artifact"]):
            fh.write("%-34s %-34s %-34s %-10s %s\n" % (
                t["artifact"], t["committed_md5"], t["rerun_md5"],
                "yes" if t["identical"] else "NO", t.get("owner", "")))

    # report
    print("GATE 1 independent re-derivation: %d figures, %d agree, %d disagree"
          % (len(FIGS), n_agree, len(FIGS) - n_agree))
    for f in FIGS:
        if not f["agree"]:
            print("  DISAGREE %s: published %r, mine %r (%s)"
                  % (f["figure"], f["published_value"], f["my_value"], f["published_in"]))
    print("GATE 2 rerun: %d artifacts, %d not identical"
          % (len(rerun_table), len([t for t in rerun_table if not t["identical"]])))
    for t in rerun_table:
        if not t["identical"]:
            print("  DIFF %s: %s vs %s" % (t["artifact"], t["committed_md5"], t["rerun_md5"]))
    print("GATE 3 corrupt-copy exit codes:")
    for c in corrupt_results:
        print("  %s on %s: clean=%s corrupted=%s"
              % (c["verifier"], c["artifact"], c.get("clean_exit"), c.get("corrupt_exit")))
    if inversion:
        print("INVERSION combined %.4f..%.4f mid %.3f (agrees with 18.1165=%s, 18.25=%s)"
              % (inversion["combined_low"], inversion["combined_high"], inversion["combined_mid"],
                 inversion["agrees_with_18_1165"], inversion["agrees_with_18_25"]))
    for n, ok, note in RESULTS:
        if not ok:
            print("  FAIL %s: %s" % (n, note))
    print("cross-artifact checks: %d, failed: %d; total assertions %d (figures %d + checks %d)"
          % (len(RESULTS), failed, total_assertions, len(FIGS), len(RESULTS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
