#!/usr/bin/env python3
"""Verifier for Phase 1 of the scale plan: ring identity.

It re-derives the headline numbers of run/eda_full_20261015/ring_identity.json,
ring_candidates.json and ring_inventory.csv by a second route, written
independently of experiments/eda_full/ring_identity.py: its own CSV parsing, its
own percentile, its own sampling replay. It also proves the aggregation rebuilds
byte identically and that no micron figure leaked into any output.

It writes nothing except when it re-runs the aggregation for the determinism
check, which is the point of that check.

Run:
    python experiments/eda_full/verify_ring_identity.py
Exit 0 when every check passes.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUN = REPO / "run" / "eda_full_20261015"
RAW = RUN / "ring_raw.tsv"
SAMPLE = RUN / "ring_sample.txt"
INV = RUN / "ring_inventory.csv"
CAND = RUN / "ring_candidates.json"
IDENT = RUN / "ring_identity.json"
DOC = REPO / "reports" / "eda_full" / "ring_identity_20261015.md"
AGENT = REPO / "experiments" / "eda_full" / "ring_identity.py"

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, note: str) -> None:
    CHECKS.append((name, bool(ok), note))


def pctl(vals, p):
    """Percentile by the nearest-rank-ish linear rule, written from scratch."""
    s = sorted(vals)
    if not s:
        return None
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * p / 100.0
    a = int(math.floor(k))
    b = int(math.ceil(k))
    if a == b:
        return float(s[a])
    return s[a] + (s[b] - s[a]) * (k - a)


def med(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None
    return float(s[n // 2]) if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def load_raw():
    pics, rings = {}, defaultdict(list)
    for line in RAW.read_text(encoding="utf-8").splitlines():
        f = line.split("\t")
        if not f:
            continue
        if f[0] == "P":
            d = {"tag": f[1], "path": f[3], "flag": f[7],
                 "Rcav": float(f[6]) if f[6] else None,
                 "dip_r": float(f[8]) if f[8] else None,
                 "dip_prom": float(f[9]) if f[9] else None,
                 "circ_r": float(f[11]) if f[11] else None,
                 "rim_r": float(f[14]) if f[14] else None}
            if f[2] not in pics or d["tag"] == "repro":
                pics[f[2]] = d
        elif f[0] == "R":
            rings[f[1]].append({"idx": int(f[2]), "radius": float(f[3]),
                                "depth": float(f[4]), "norm": float(f[12])})
    return pics, rings


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> int:
    ident = json.loads(IDENT.read_text(encoding="utf-8"))
    cand = json.loads(CAND.read_text(encoding="utf-8"))
    pics, rings = load_raw()

    # -- 1. sample replay from the fixed seeds -------------------------------
    sample_rows = list(csv.DictReader(SAMPLE.open(encoding="utf-8")))
    chk_trimm = json.loads(IDENT.read_text(encoding="utf-8"))
    # replay population A only: 400 per line from picture_table, seed 20261015
    lib_folders = {"ICube Defects Library", "Updated ICube Objects 20260915",
                   "Updated ICube Categorical Classes 20260915"}
    pool = defaultdict(list)
    for r in csv.DictReader((RUN / "picture_table.csv").open(encoding="utf-8")):
        if r["winning_path"].split("/", 1)[0] in lib_folders:
            pool[r["line"]].append(r)
    rng = random.Random(20261015)
    replay = set()
    for ln in ["L24", "L25", "L26", "L27", "L31"]:
        for r in rng.sample(sorted(pool[ln], key=lambda x: x["md5"]), 400):
            replay.add(r["md5"])
    lib_in_file = {r["md5"] for r in sample_rows if r["tag"] == "lib"}
    check("population_A_replays_from_seed", replay == lib_in_file,
          "seed 20261015 gives %d library rows, ring_sample.txt holds %d, "
          "identical=%s" % (len(replay), len(lib_in_file), replay == lib_in_file))
    check("sample_row_count", len(sample_rows) == 2700,
          "ring_sample.txt rows %d, expected 2700" % len(sample_rows))

    # -- 2. picture counts ----------------------------------------------------
    ok = [m for m, d in pics.items() if d["flag"] == "ok" and d["Rcav"]]
    check("pictures_ok_matches", len(ok) == ident["sample"]["pictures_ok"],
          "raw ok pictures %d, ring_identity.json says %d"
          % (len(ok), ident["sample"]["pictures_ok"]))
    check("inventory_rows_match",
          sum(1 for _ in INV.open(encoding="utf-8")) - 1 == think_rows(rings, pics),
          "ring_inventory.csv rows %d, R rows in raw %d"
          % (sum(1 for _ in INV.open(encoding="utf-8")) - 1, think_rows(rings, pics)))

    # -- 3. the prior run reproduced, second route ---------------------------
    repro = [m for m, d in pics.items() if d["tag"] == "repro"]
    acc = [2.0 * pics[m]["dip_r"] for m in repro if pics[m]["flag"] == "ok"
           and pics[m]["dip_prom"] is not None and pics[m]["dip_prom"] > 1.0]
    s = sorted(acc)
    k = int(len(s) * 0.15)
    tmean = sum(s[k:len(s) - k]) / len(s[k:len(s) - k])
    rec = ident["methods"]["prior_run_reproduction"]
    check("repro_frames_200", len(repro) == 200,
          "repro tagged pictures %d" % len(repro))
    check("repro_trimmed_mean_second_route",
          abs(tmean - rec["trimmed_mean_lens_diam_px"]) < 0.05,
          "second route %.2f px, JSON %.2f px" % (tmean, rec["trimmed_mean_lens_diam_px"]))
    check("repro_within_one_px_of_783_8", abs(tmean - 783.8) <= 1.0,
          "delta from 783.8 is %.2f px" % (tmean - 783.8))

    # -- 4. the headline diameter, second route ------------------------------
    rim = [2.0 * pics[m]["rim_r"] for m in ok if pics[m]["rim_r"] is not None]
    v = ident["verdict"]["lens_diameter_px"]
    check("headline_median_second_route", abs(med(rim) - v["median_diam_px"]) < 0.05,
          "second route %.2f px, JSON %.2f px" % (med(rim), v["median_diam_px"]))
    check("headline_p25_p75_second_route",
          abs(pctl(rim, 25) - v["p25_diam_px"]) < 0.2
          and abs(pctl(rim, 75) - v["p75_diam_px"]) < 0.2,
          "second route p25/p75 %.2f/%.2f, JSON %.2f/%.2f"
          % (pctl(rim, 25), pctl(rim, 75), v["p25_diam_px"], v["p75_diam_px"]))
    check("headline_n_matches", len(rim) == v["n"],
          "second route n %d, JSON n %d" % (len(rim), v["n"]))

    # -- 5. the wide band figure, second route -------------------------------
    wide = [2.0 * pics[m]["circ_r"] for m in ok if pics[m]["circ_r"] is not None]
    wm = ident["methods"]["circle_fit_wide_0.50_1.06"]["median_diam_px"]
    check("wide_band_median_second_route", abs(med(wide) - wm) < 0.05,
          "second route %.2f px, JSON %.2f px" % (med(wide), wm))
    check("wide_band_near_earlier_848", abs(med(wide) - 848.0) < 20.0,
          "wide band median %.1f px against the earlier 848 px" % med(wide))

    # -- 6. candidate ring statistics, second route --------------------------
    climit = {c["candidate_index"]: c for c in cand["candidates"]}
    for ci, c in climit.items():
        lo, hi = c["norm_window"]
        # assign each picture's deepest ring in the window, recomputed here
        rv, det = [], 0
        for m in ok:
            w = [r for r in rings[m] if lo <= r["norm"] < hi]
            if not w:
                continue
            det += 1
            rv.append(max(w, key=lambda r: r["depth"])["radius"])
        check("candidate_%d_median_radius_second_route" % ci,
              abs(med(rv) - c["overall"]["median_radius_px"]) < 0.05,
              "second route %.2f px, JSON %.2f px"
              % (med(rv), c["overall"]["median_radius_px"]))
        check("candidate_%d_iqr_second_route" % ci,
              abs(pctl(rv, 25) - c["overall"]["iqr_radius_px"][0]) < 0.2
              and abs(pctl(rv, 75) - c["overall"]["iqr_radius_px"][1]) < 0.2,
              "second route IQR %.2f-%.2f, JSON %s"
              % (pctl(rv, 25), pctl(rv, 75), c["overall"]["iqr_radius_px"]))
        check("candidate_%d_detection_rate_second_route" % ci,
              abs(det / len(ok) - c["detection_rate"]) < 0.001,
              "second route %.4f, JSON %.4f" % (det / len(ok), c["detection_rate"]))

    # -- 7. discriminator 1, second route ------------------------------------
    lab = defaultdict(set)
    for r in csv.DictReader((RUN / "resolved_labels.csv").open(encoding="utf-8")):
        if r["canonical_id"] in ("missing_lens", "lens_off_center"):
            lab[r["picture_md5"]].add(r["canonical_id"])
    nl = [m for m in ok if "missing_lens" in lab.get(m, ())]
    other = [m for m in ok if not (lab.get(m))]
    for ci, c in climit.items():
        lo, hi = c["norm_window"]

        def rate(ms):
            if not ms:
                return None
            return sum(1 for m in ms if any(lo <= r["norm"] < hi for r in rings[m])) / len(ms)
        r_o = rate(other)
        r_n = rate(nl)
        e = c["detection_rate_by_group"]
        check("D1_candidate_%d_rates_second_route" % ci,
              abs(r_o - e["other"]) < 0.001 and abs(r_n - e["missing_lens"]) < 0.001,
              "second route other %.4f missing_lens %.4f, JSON %.4f / %.4f"
              % (r_o, r_n, e["other"], e["missing_lens"]))
    check("D1_rings_per_picture_second_route",
          abs(sum(len(rings[m]) for m in nl) / len(nl)
              - ident["discriminators"]["discriminator_1_missing_lens"]["rings_per_picture"]["missing_lens"])
          < 0.001,
          "missing-lens rings per picture %.4f"
          % (sum(len(rings[m]) for m in nl) / len(nl)))

    # -- 8. no micron figure anywhere ----------------------------------------
    forbidden = re.compile(r"(\b14200\b|14[ ,_]200|18\.1165|18\.25\b|px_per_mm|um_per_px|mm_per_px"
                           r"|\d[\d,\.]*\s*(µm|micron|microns|micrometre|micrometres|um\b|mm\b))")
    bad = []
    for p in (INV, CAND, IDENT, SAMPLE, RAW, DOC, AGENT,
              REPO / "vm" / "ops" / "scan_rings.py"):
        txt = p.read_text(encoding="utf-8", errors="replace")
        for mt in forbidden.finditer(txt):
            frag = txt[max(0, mt.start() - 40):mt.end() + 40].replace("\n", " ")
            if "NOMINAL_LENS_DIAMETER_UM = 14_200.0" in frag:
                continue          # the constant kept solely to reproduce the prior method
            bad.append("%s: %s" % (p.name, mt.group(0)))
    check("no_micron_figure_in_any_output", not bad,
          "hits: %s" % (bad[:6] if bad else "none"))

    # -- 9. doc header --------------------------------------------------------
    head = DOC.read_text(encoding="utf-8").splitlines()[:6]
    check("doc_five_line_header",
          head[0] == "---" and head[1].startswith("title:") and head[2] == "date: 2026-10-15"
          and head[3] == "type: result" and head[4] == "status: active"
          and head[5] == "where: reports/eda_full/ring_identity_20261015.md",
          "header %r" % (head,))

    # -- 10. byte identical rebuild ------------------------------------------
    before = {p.name: md5(p) for p in (INV, CAND, IDENT, SAMPLE)}
    subprocess.run([sys.executable, str(AGENT), "--aggregate"],
                   cwd=str(REPO), capture_output=True, check=True)
    after = {p.name: md5(p) for p in (INV, CAND, IDENT, SAMPLE)}
    check("aggregation_rebuild_is_byte_identical", before == after,
          "before %s after %s" % (before, after))

    failed = [c for c in CHECKS if not c[1]]
    for name, okk, note in CHECKS:
        print("[%s] %s: %s" % ("ok" if okk else "FAIL", name, note))
    print("checks: %d, failed: %d" % (len(CHECKS), len(failed)))
    return 1 if failed else 0


def think_rows(rings, pics):
    """R rows in the raw file for pictures that survived into the picture dict."""
    n = 0
    for line in RAW.read_text(encoding="utf-8").splitlines():
        f = line.split("\t")
        if f[0] == "R" and f[1] in pics:
            n += 1
    return n


if __name__ == "__main__":
    sys.exit(main())
