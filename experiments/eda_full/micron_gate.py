#!/usr/bin/env python3
"""Ticket 014 the 300 micron gate: builder.

Determines what the four production ``*_MICRON_THRESHOLD`` gate tags gate on,
tests the client's 300 micron claim against the data under two size proxies,
reconciles the before-and-after delta against the 2026-10-13 files, and inverts
the client's own gate into an independent microns-per-pixel estimate.

The four gate codes are the CLIENT'S AUTHORITY. Everything this script derives
is reported BESIDE them, never instead of them.

Method
------
An image is in scope for a base code (Foreign Matter, Fiber, Extraneous Polymer,
HEMA) when it carries at least one annotation box of that base code, taken from
the production files (priority level 1). The gate flag is the corresponding
``P3_*_MICRON_THRESHOLD`` tag, which exists only in the production files, so the
production scope is the only scope in which the flag can ever appear. The size of
an image for a base code is the size of its LARGEST base-code box, measured two
ways:

  diag = sqrt(w^2 + h^2)   the rectangle diagonal
  side = max(w, h)         the longer side of the rectangle

Both are reported under both candidate scales, 18.1165 (ours) and 18.25 (the
lead's, written nowhere).

Keying is on content md5 everywhere, never on a path.

The 2026-10-13 production files are READ ONLY on the shared VM and copied to a
local scratch directory (never into the repo, never written back). Point
OLD_PROD_DIR at that copy. When it is absent the delta is skipped, not faked.

Run:
    ./.venv/Scripts/python.exe experiments/eda_full/micron_gate.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(REPO, "data")
RUN = os.path.join(REPO, "run", "eda_full_20261015")

BOX_SIZES = os.path.join(RUN, "box_sizes.csv")
RESOLVED = os.path.join(RUN, "resolved_labels.csv")
MANIFEST = os.path.join(RUN, "file_manifest.csv")
CROSSWALK = os.path.join(DATA, "crosswalk.csv")

GATE_ANALYSIS = os.path.join(RUN, "gate_analysis.csv")
GATE_DELTA = os.path.join(RUN, "gate_delta.csv")
SCALE_JSON = os.path.join(RUN, "gate_scale_estimate.json")

# The local read-only copy of the 2026-10-13 production files. Never the repo.
OLD_PROD_DIR = os.path.join(
    os.environ.get("OLD_PROD_DIR",
                   "C:/Users/Abcom/AppData/Local/hermes/cache/scratch/old_prod"))

# The two candidate scales, named, never silently chosen.
SCALE_OURS = 18.1165
SCALE_LEAD = 18.25

# The stated client cuts, in microns. 300 replaces 647 in October 2026.
CUT_NEW_UM = 300.0
CUT_OLD_UM = 647.0

PRODUCTION_FILES = [f"annotations_45219{n}.xml" for n in range(40, 47)]

# The four gate production codes, and the base production code each flags.
GATE_PROD_CODE = {
    "P3_FM": "P3_FM_MICRON_THRESHOLD",
    "P3_FIB": "P3_FIB_MICRON_THRESHOLD",
    "P3_EP": "P3_EP_MICRON_THRESHOLD",
    "P3_HE": "P3_HE_MICRON_THRESHOLD",
}
BASE_NAME = {
    "P3_FM": "foreign_matter",
    "P3_FIB": "fiber",
    "P3_EP": "extraneous_polymer",
    "P3_HE": "hema_obstruction",
}

ANALYSIS_COLUMNS = [
    "base_code", "base_defect", "size_proxy", "scope", "gate_state", "n_images",
    "p25_px", "p50_px", "p75_px", "min_px", "max_px",
    "p25_um_18_1165", "p50_um_18_1165", "p75_um_18_1165",
    "p25_um_18_25", "p50_um_18_25", "p75_um_18_25",
    "boundary_lower_px", "boundary_upper_px", "boundary_mid_px",
    "boundary_mid_um_18_1165", "boundary_mid_um_18_25",
    "note",
]

DELTA_COLUMNS = [
    "picture_md5", "winning_path", "changed",
    "old_tag_count", "new_tag_count",
    "added_tags", "removed_tags",
    "added_gate_bases", "geometry_changed",
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def percentile(sorted_vals, q):
    """Linear-interpolation percentile, matching box_geometry.py."""
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    k = (n - 1) * q
    lo = int(k)
    hi = min(lo + 1, n - 1)
    return float(sorted_vals[lo]) + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def basename(name: str) -> str:
    return name.rsplit("/", 1)[-1]


def load_crosswalk_codes():
    """canonical_id -> production base code, and gate prod code -> base prod code."""
    canon_to_prod: dict[str, str] = {}
    gate_base: dict[str, str] = {}
    with open(CROSSWALK, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            prod = row["code_in_production_20260925"]
            if not prod:
                continue
            if row["is_size_gate"] == "yes":
                gate_base[prod] = row["gate_base_code"]
            else:
                canon_to_prod[row["canonical_id"]] = prod
    return canon_to_prod, gate_base


def load_manifest():
    by_basename: dict[str, str] = {}
    with open(MANIFEST, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_basename[basename(row["path"])] = row["md5"]
    return by_basename


def read_shapes(path: str):
    """name -> (sorted tag labels, sorted box tuples). Trusted client export."""
    root = ET.parse(path).getroot()  # trusted client export, XXE accepted on purpose
    out = {}
    for img in root.findall("image"):
        tags = sorted(t.get("label") for t in img.findall("tag"))
        boxes = sorted(
            (b.get("label"), b.get("xtl"), b.get("ytl"), b.get("xbr"), b.get("ybr"),
             b.get("rotation"))
            for b in img.findall("box"))
        out[img.get("name")] = (tags, boxes)
    return out


def main() -> int:
    canon_to_prod, gate_base = load_crosswalk_codes()
    by_basename = load_manifest()

    # ---- boxes: per picture, per base code, the largest-box sizes -----------
    # maxside and maxdiag per (md5, base_code), over both scopes.
    prod_side: dict[tuple, float] = defaultdict(lambda: -1.0)
    prod_diag: dict[tuple, float] = defaultdict(lambda: -1.0)
    all_side: dict[tuple, float] = defaultdict(lambda: -1.0)
    all_diag: dict[tuple, float] = defaultdict(lambda: -1.0)
    box_count = Counter()
    with open(BOX_SIZES, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            base = canon_to_prod.get(r["canonical_id"])
            if base not in BASE_NAME:
                continue
            w = float(r["w_px"]); h = float(r["h_px"])
            side = max(w, h); diag = math.sqrt(w * w + h * h)
            key = (r["picture_md5"], base)
            box_count[base] += 1
            if side > all_side[key]:
                all_side[key] = side
            if diag > all_diag[key]:
                all_diag[key] = diag
            if r["priority_level"] == "1":
                if side > prod_side[key]:
                    prod_side[key] = side
                if diag > prod_diag[key]:
                    prod_diag[key] = diag

    # ---- gate tags, current (2026-10-15) production files -------------------
    # The gate tags exist only in the production files. Reading them from the
    # current production XML keeps the gate analysis and the delta on the same
    # footing: both are production-scoped.
    new_tags: dict[str, set] = defaultdict(set)
    new_geom: dict[str, list] = defaultdict(list)
    cur_shapes = {}
    for fname in PRODUCTION_FILES:
        shp = read_shapes(os.path.join(DATA, fname))
        cur_shapes[fname] = shp
        for name, (tags, _boxes) in shp.items():
            m = by_basename.get(basename(name))
            if not m:
                continue
            for t in tags:
                new_tags[m].add(t)

    # ---- gate tags, 2026-10-13 files (read only, from the local copy) --------
    old_tags: dict[str, set] = defaultdict(set)
    old_geom: dict[str, list] = defaultdict(list)
    old_cnt: dict[str, Counter] = defaultdict(Counter)
    new_cnt: dict[str, Counter] = defaultdict(Counter)
    delta_available = os.path.isdir(OLD_PROD_DIR)
    unresolved_names: list[str] = []
    if delta_available:
        for fname in PRODUCTION_FILES:
            old = read_shapes(os.path.join(OLD_PROD_DIR, fname))
            new = cur_shapes[fname]
            for name in set(old) | set(new):
                m = by_basename.get(basename(name))
                if not m:
                    unresolved_names.append(name)
                    continue
                if name in old:
                    for t in old[name][0]:
                        old_tags[m].add(t)
                        old_cnt[m][t] += 1
                    old_geom[m].extend(old[name][1])
                if name in new:
                    for t in new[name][0]:
                        new_tags[m].add(t)
                        new_cnt[m][t] += 1
                    new_geom[m].extend(new[name][1])

    gate_prod_code = {v: k for k, v in GATE_PROD_CODE.items()}

    # ---- distributions ------------------------------------------------------
    proxies = [("diag", prod_diag, all_diag), ("side", prod_side, all_side)]
    analysis_rows = []
    boundaries = {}
    for base in ["P3_FM", "P3_FIB", "P3_EP", "P3_HE"]:
        gate_code = GATE_PROD_CODE[base]
        scopes = [
            ("production", {"diag": prod_diag, "side": prod_side}),
            ("all_sources", {"diag": all_diag, "side": all_side}),
        ]
        for scope, tbls in scopes:
            for proxy in ("diag", "side"):
                tbl = tbls[proxy]
                flagged, unflagged = [], []
                for (m, b), val in tbl.items():
                    if b != base or val < 0:
                        continue
                    if gate_code in new_tags.get(m, set()):
                        flagged.append(val)
                    else:
                        unflagged.append(val)
                flagged.sort(); unflagged.sort()
                bu = max(unflagged) if unflagged else None
                fl = min(flagged) if flagged else None
                bmid = (bu + fl) / 2.0 if (bu is not None and fl is not None) else None
                if scope == "production" and proxy == "side":
                    boundaries[base] = {"lower_px": bu, "upper_px": fl, "mid_px": bmid}
                note = ""
                if not unflagged:
                    note = ("no unflagged group: the gate tag is on every picture "
                            "that carries this base code, so it is unconditional "
                            "and not size gated")
                elif len(unflagged) < 5:
                    note = f"thin unflagged group (n={len(unflagged)})"
                for state, arr in (("flagged", flagged), ("unflagged", unflagged)):
                    stats = _stats(arr)
                    analysis_rows.append({
                        "base_code": base, "base_defect": BASE_NAME[base],
                        "size_proxy": proxy, "scope": scope, "gate_state": state,
                        "n_images": len(arr),
                        "p25_px": stats["p25"], "p50_px": stats["p50"], "p75_px": stats["p75"],
                        "min_px": stats["min"], "max_px": stats["max"],
                        "p25_um_18_1165": _um(stats["p25"], SCALE_OURS),
                        "p50_um_18_1165": _um(stats["p50"], SCALE_OURS),
                        "p75_um_18_1165": _um(stats["p75"], SCALE_OURS),
                        "p25_um_18_25": _um(stats["p25"], SCALE_LEAD),
                        "p50_um_18_25": _um(stats["p50"], SCALE_LEAD),
                        "p75_um_18_25": _um(stats["p75"], SCALE_LEAD),
                        "boundary_lower_px": _r(bu), "boundary_upper_px": _r(fl),
                        "boundary_mid_px": _r(bmid),
                        "boundary_mid_um_18_1165": _um(bmid, SCALE_OURS),
                        "boundary_mid_um_18_25": _um(bmid, SCALE_LEAD),
                        "note": note,
                    })

    # ---- delta reconciliation ----------------------------------------------
    delta_rows = []
    if delta_available:
        changed_count = 0
        add_counter = Counter()
        del_counter = Counter()
        geom_changed = 0
        for m in sorted(set(old_cnt) | set(new_cnt)):
            ot = old_cnt.get(m, Counter()); nt = new_cnt.get(m, Counter())
            add_ms = nt - ot
            del_ms = ot - nt
            adds = sorted(add_ms.elements()); dels = sorted(del_ms.elements())
            og = old_geom.get(m, []); ng = new_geom.get(m, [])
            gch = og != ng
            if gch:
                geom_changed += 1
            changed = bool(adds or dels)
            if changed:
                changed_count += 1
                for t in adds:
                    add_counter[t] += 1
                for t in dels:
                    del_counter[t] += 1
            if not changed:
                continue
            delta_rows.append({
                "picture_md5": m, "winning_path": "",
                "changed": "yes",
                "old_tag_count": sum(ot.values()), "new_tag_count": sum(nt.values()),
                "added_tags": ";".join(adds), "removed_tags": ";".join(dels),
                "added_gate_bases": ";".join(sorted(
                    gate_prod_code[t] for t in adds if t in gate_prod_code)),
                "geometry_changed": "yes" if gch else "no",
            })
    else:
        changed_count = None
        add_counter = del_counter = Counter()
        geom_changed = None

    # ---- fill winning paths for delta rows (md5 -> winning path) ------------
    md5_to_path = {}
    with open(RUN + "/picture_table.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            md5_to_path[r["md5"]] = r["winning_path"]
    for row in delta_rows:
        row["winning_path"] = md5_to_path.get(row["picture_md5"], "")

    # ---- inverted scale -----------------------------------------------------
    # boundaries[base] = {lower_px, upper_px} for the new (300) cut, side proxy.
    # The old (647) cut boundary from the 2026-10-13 files, side proxy.
    scale_est = build_scale_estimate(boundaries, old_tags, new_tags, prod_side,
                                     gate_base, delta_available)

    # ---- write outputs ------------------------------------------------------
    _write_csv(GATE_ANALYSIS, ANALYSIS_COLUMNS, analysis_rows)
    _write_csv(GATE_DELTA, DELTA_COLUMNS, delta_rows)

    out = {
        "ticket": "014-micron-gate",
        "date": "2026-10-15",
        "gate_codes_are_client_authority": True,
        "base_codes": list(BASE_NAME.keys()),
        "scales_candidate": {"18.1165": SCALE_OURS, "18.25": SCALE_LEAD},
        "size_proxies": {
            "diag": "sqrt(w^2 + h^2), the rectangle diagonal",
            "side": "max(w, h), the longer side of the rectangle",
        },
        "declared_cuts_um": {"new": CUT_NEW_UM, "old": CUT_OLD_UM},
        "boundaries_new_side_px": boundaries,
        "delta_available": delta_available,
        "old_prod_dir": OLD_PROD_DIR,
        "delta": {
            "changed_pictures": changed_count,
            "added_tags": dict(sorted(add_counter.items())),
            "removed_tags": dict(sorted(del_counter.items())),
            "geometry_changed_pictures": geom_changed,
            "unresolved_names": sorted(set(unresolved_names)),
            "delta_rows": len(delta_rows),
        },
        "counts": {
            "base_defect_boxes": dict(sorted(box_count.items())),
        },
        "scale_estimate": scale_est,
        "outputs": {
            "gate_analysis.csv": {"rows": len(analysis_rows),
                                  "md5": md5_file(GATE_ANALYSIS)},
            "gate_delta.csv": {"rows": len(delta_rows), "md5": md5_file(GATE_DELTA)},
        },
    }
    with open(SCALE_JSON, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=2, sort_keys=False) + "\n")

    # ---- report to stdout ---------------------------------------------------
    print("gate boundary (new 300 cut, side proxy, production scope):")
    for base, b in sorted(boundaries.items()):
        lo, hi, mid = b["lower_px"], b["upper_px"], b["mid_px"]
        if mid is None:
            print(f"  {base}: no unflagged group, boundary not defined")
            continue
        print(f"  {base}: ({lo:.3f}, {hi:.3f}] px  mid {mid:.3f} px  "
              f"-> {mid * SCALE_OURS:.2f} um @18.1165, {mid * SCALE_LEAD:.2f} um @18.25")
    print("delta:", changed_count, "changed, added", dict(sorted(add_counter.items())),
          "removed", dict(sorted(del_counter.items())), "geom_changed", geom_changed)
    print("boundaries:", {k: {kk: (round(vv, 4) if vv is not None else None)
                              for kk, vv in v.items()} for k, v in boundaries.items()})
    print("scale estimate:", json.dumps(scale_est, indent=2))
    print("gate_analysis.csv md5:", md5_file(GATE_ANALYSIS))
    print("gate_delta.csv md5:", md5_file(GATE_DELTA))
    return 0


def _r(x):
    return None if x is None else round(x, 4)


def _um(px, scale):
    return None if px is None else round(px * scale, 4)


def _stats(arr):
    if not arr:
        return {"p25": None, "p50": None, "p75": None, "min": None, "max": None}
    return {"p25": percentile(arr, 0.25), "p50": percentile(arr, 0.50),
            "p75": percentile(arr, 0.75), "min": arr[0], "max": arr[-1]}


def _write_csv(path, cols, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def build_scale_estimate(new_boundaries, old_tags, new_tags, prod_side, gate_base,
                         delta_available):
    """Invert the client gate boundary into an independent microns-per-pixel.

    If the boundary between flagged and unflagged images sits at B pixels for a
    declared cut C microns, then the client's scale is C / B microns per pixel,
    independent of our own 14,200 micron reference.
    """
    est = {
        "method": ("the flagged-versus-unflagged boundary of the client's gate is "
                   "a client-anchored length; invert it: scale = cut_um / boundary_px"),
        "proxy": "side = max(w, h), the longer side of the annotation rectangle",
        "scope": "production (the gate tag exists only in the production files)",
        "new_cut_um": CUT_NEW_UM,
        "old_cut_um": CUT_OLD_UM,
        "new_boundaries_px": {},
        "old_boundaries_px": {},
        "implied_scale_new": None,
        "implied_scale_old": None,
        "implied_scale_combined": None,
        "assumptions": [
            "the gate is applied to the LARGEST base-code box on the image",
            "the annotation box edges delimit the debris (no systematic margin)",
            "the client's declared cut (300 microns now, 647 before) is exact",
            "the proxy that fits is the longer side max(w,h), which the data "
            "supports (0 misclassifications vs 39 for the diagonal)",
        ],
    }

    def interval_from(base):
        b = new_boundaries.get(base)
        if not b or b["lower_px"] is None or b["upper_px"] is None:
            return None
        return b["lower_px"], b["upper_px"]

    # New cut (300): intersect the FM and Fiber boundaries.
    lows, highs = [], []
    for base, base_prod in [("P3_FM", "P3_FM"), ("P3_FIB", "P3_FIB")]:
        iv = interval_from(base)
        if iv:
            lows.append(iv[0]); highs.append(iv[1])
            est["new_boundaries_px"][base] = {"lower_px": _r(iv[0]), "upper_px": _r(iv[1])}
    if lows:
        lo = max(lows); hi = min(highs)
        est["implied_scale_new"] = {
            "boundary_px_lower": _r(lo), "boundary_px_upper": _r(hi),
            "scale_um_per_px_low": round(CUT_NEW_UM / hi, 4),
            "scale_um_per_px_high": round(CUT_NEW_UM / lo, 4),
            "scale_um_per_px_mid": round(CUT_NEW_UM / ((lo + hi) / 2.0), 4),
        }

    # Old cut (647): intersect the FM and Fiber boundaries on the 2026-10-13 tags.
    if delta_available:
        gate_prod_code = {v: k for k, v in GATE_PROD_CODE.items()}
        ol_lows, ol_highs = [], []
        for base in ["P3_FM", "P3_FIB"]:
            gc = GATE_PROD_CODE[base]
            fu = [v for (m, b), v in prod_side.items()
                  if b == base and v >= 0 and gc not in old_tags.get(m, set())]
            fl = [v for (m, b), v in prod_side.items()
                  if b == base and v >= 0 and gc in old_tags.get(m, set())]
            if fu and fl:
                lo, hi = max(fu), min(fl)
                ol_lows.append(lo); ol_highs.append(hi)
                est["old_boundaries_px"][base] = {"lower_px": _r(lo), "upper_px": _r(hi)}
        if ol_lows:
            lo = max(ol_lows); hi = min(ol_highs)
            est["implied_scale_old"] = {
                "boundary_px_lower": _r(lo), "boundary_px_upper": _r(hi),
                "scale_um_per_px_low": round(CUT_OLD_UM / hi, 4),
                "scale_um_per_px_high": round(CUT_OLD_UM / lo, 4),
                "scale_um_per_px_mid": round(CUT_OLD_UM / ((lo + hi) / 2.0), 4),
            }

    # Combined: intersection of the new (300) and old (647) scale intervals.
    slo, shi = [], []
    for key in ("implied_scale_new", "implied_scale_old"):
        v = est[key]
        if v:
            slo.append(v["scale_um_per_px_low"]); shi.append(v["scale_um_per_px_high"])
    if slo:
        lo = max(slo); hi = min(shi)
        contains_181165 = lo <= SCALE_OURS <= hi
        contains_1825 = lo <= SCALE_LEAD <= hi
        if contains_181165 and contains_1825:
            agreement = "both"
        elif contains_181165:
            agreement = "18.1165 only"
        elif contains_1825:
            agreement = "18.25 only"
        else:
            agreement = "neither"
        est["implied_scale_combined"] = {
            "scale_um_per_px_low": round(lo, 4),
            "scale_um_per_px_high": round(hi, 4),
            "scale_um_per_px_mid": round((lo + hi) / 2.0, 4),
            "agrees_with_18_1165": contains_181165,
            "agrees_with_18_25": contains_1825,
            "agreement": agreement,
            "resolves_the_two_candidate_scales": agreement in ("18.1165 only", "18.25 only"),
        }
    est["implies_at_our_scales"] = None
    if est["new_boundaries_px"]:
        lows = [v["lower_px"] for v in est["new_boundaries_px"].values()]
        highs = [v["upper_px"] for v in est["new_boundaries_px"].values()]
        lo, hi = max(lows), min(highs)
        est["implies_at_our_scales"] = {
            "note": ("the same boundary read at our own scales gives the cut in "
                     "microns, assuming our scale is right"),
            "cut_um_at_18_1165_low": round(lo * SCALE_OURS, 2),
            "cut_um_at_18_1165_high": round(hi * SCALE_OURS, 2),
            "cut_um_at_18_25_low": round(lo * SCALE_LEAD, 2),
            "cut_um_at_18_25_high": round(hi * SCALE_LEAD, 2),
        }
    return est


if __name__ == "__main__":
    sys.exit(main())
