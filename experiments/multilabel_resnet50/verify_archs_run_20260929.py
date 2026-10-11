#!/usr/bin/env python3
"""Independent re-check of the 2026-09-29 multilabel architecture sweep.

For every architecture run it recomputes each headline metric and every per-class
confusion count from the raw prediction dump and asserts they match metrics.json,
checks the dump holds exactly the 677 test rows of the frozen split, checks the
checkpoint's own architecture and parameter count against the values verify_archs.py
proved, and checks the timing block is present, no-warmup and internally consistent.

Then it prints the comparison table (Folded Lens first, because that is the ask) and
the deltas against the plain ResNet50 control of the same session.

    python verify_archs_run_20260929.py
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train as T  # noqa: E402

RUN = Path("run/multilabel_lp_archs_20260929")
SPLIT = Path("experiments/multilabel_resnet50/splits/variant_80_20_two_way.csv")
BASE_20260928 = Path("run/multilabel_lp_20260928/metrics.json")
# Parameter counts proved by verify_archs.py on the VM (torch, 5-class head).
EXPECTED_PARAMS = {
    T.ARCH_RESNET50: 23_518_277,
    T.ARCH_MULTISCALE: 58_438_725,
    T.ARCH_MULTILVL_ATTENTION: 50_435_877,
    T.ARCH_INCEPTION_ATTENTION: 58_635_682,
    T.ARCH_INCEPTION_REFINE: 45_876_293,
}
checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print("  %-52s %s %s" % (name, "PASS" if ok else "FAIL", detail))


def average_precision(y_true, y_score):
    order = np.argsort(-y_score, kind="stable")
    hits = y_true[order]
    tp = np.cumsum(hits)
    precision = tp / np.arange(1, len(hits) + 1)
    recall = tp / y_true.sum()
    return float((np.diff(np.concatenate([[0.0], recall])) * precision).sum())


def load_split_test_rows():
    rows = list(csv.DictReader(open(SPLIT, newline="", encoding="utf-8")))
    return sorted(r["image_path"] for r in rows if r["split"] == "test")


split_test = load_split_test_rows()
print("split test rows: %d" % len(split_test))

results = {}
for arch in T.ARCHS:
    run_dir = RUN / ("runs/%s_20260929" % arch)
    print("\n[%s]" % arch)
    if not (run_dir / "metrics.json").is_file():
        check("%s metrics.json exists" % arch, False, str(run_dir))
        continue
    m = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    tm = m["test_metrics"]
    d = np.load(run_dir / "test_predictions.npz", allow_pickle=False)
    y_true = d["y_true"].astype(int)
    y_score = d["y_score"]
    classes = [c if isinstance(c, str) else c.decode("utf-8") for c in d["classes"]]
    y_pred = (y_score >= 0.5).astype(int)
    tp = ((y_true == 1) & (y_pred == 1)).sum(0)
    fp = ((y_true == 0) & (y_pred == 1)).sum(0)
    fn = ((y_true == 1) & (y_pred == 0)).sum(0)
    tn = ((y_true == 0) & (y_pred == 0)).sum(0)
    prec = tp / np.maximum(tp + fp, 1)
    rec = tp / np.maximum(tp + fn, 1)
    f1 = 2 * prec * rec / np.maximum(prec + rec, 1e-12)
    aps = [average_precision(y_true[:, j], y_score[:, j]) for j in range(y_true.shape[1])]

    check("%s classes order" % arch, classes == T.LP_TAGS, str(classes))
    check("%s macro AUPRC recomputes" % arch, abs(tm["macro_auprc"] - float(np.mean(aps))) < 1e-4,
          "%.5f vs %.5f" % (float(np.mean(aps)), tm["macro_auprc"]))
    check("%s macro F1 recomputes" % arch, abs(tm["macro_f1"] - float(f1.mean())) < 1e-4,
          "%.5f vs %.5f" % (float(f1.mean()), tm["macro_f1"]))
    check("%s hamming loss recomputes" % arch, tm["hamming_loss"] == round(float((y_true != y_pred).mean()), 5))
    check("%s exact match recomputes" % arch, tm["exact_match_ratio"] == round(float((y_true == y_pred).all(1).mean()), 5))
    check("%s micro precision/recall" % arch,
          abs(tm["micro_precision"] - float(tp.sum() / (tp + fp).sum())) < 1e-4
          and abs(tm["micro_recall"] - float(tp.sum() / (tp + fn).sum())) < 1e-4)
    ok_counts = all(tm["per_class"][c]["tp"] == int(tp[j]) and tm["per_class"][c]["fp"] == int(fp[j])
                    and tm["per_class"][c]["fn"] == int(fn[j]) and tm["per_class"][c]["tn"] == int(tn[j])
                    for j, c in enumerate(classes))
    check("%s all 20 confusion counts match" % arch, ok_counts,
          str([(classes[j], int(tp[j]), int(fp[j]), int(fn[j]), int(tn[j])) for j in range(5)]))
    paths = sorted(p if isinstance(p, str) else p.decode("utf-8") for p in d["paths"])
    check("%s npz rows are the 677 test rows" % arch, paths == split_test, "%d rows" % len(paths))
    check("%s arch recorded in metrics" % arch, m.get("arch") == arch, str(m.get("arch")))
    check("%s param count as verified" % arch, m.get("params_total") == EXPECTED_PARAMS[arch],
          "%s vs %s" % (m.get("params_total"), EXPECTED_PARAMS[arch]))
    hist = list(csv.DictReader(open(run_dir / "history.csv", newline="", encoding="utf-8")))
    check("%s 50 epochs in history" % arch, len(hist) == 50, "%d" % len(hist))
    ti = m.get("timing", {})
    check("%s timing block present, no warmup" % arch,
          ti.get("warmup_used") is False and ti.get("images") == len(split_test),
          "images=%s warmup_used=%s" % (ti.get("images"), ti.get("warmup_used")))
    check("%s cold and steady per-image numbers" % arch,
          (ti.get("inference_ms_per_image_cold") or 0) > 0 and (ti.get("inference_ms_per_image_steady_median") or 0) > 0,
          "cold %s ms, steady %s ms, first batch %s ms"
          % (ti.get("inference_ms_per_image_cold"), ti.get("inference_ms_per_image_steady_median"),
             ti.get("inference_first_batch_ms_cold")))
    check("%s training seconds match the summed epoch history" % arch,
          abs(ti.get("train_seconds_total", 0) - sum(float(h["seconds"]) for h in hist)) < 2.0,
          "%s vs %.1f" % (ti.get("train_seconds_total"), sum(float(h["seconds"]) for h in hist)))
    check("%s taps resolved to the notebook's add layers" % arch,
          m.get("taps") == "n/a (baseline has no taps)" or m.get("taps") == "pre-activation residual add",
          str(m.get("taps")))
    results[arch] = {"m": m, "tm": tm, "f1": f1, "prec": prec, "rec": rec, "aps": aps,
                     "hist": hist, "timing": ti}

print("\n%d checks, %d failed" % (len(checks), sum(1 for _, ok, _ in checks if not ok)))

if len(results) == len(T.ARCHS):
    print("\n=== test set, 677 images, threshold 0.5 ===")
    print("%-30s %11s %7s %7s %7s %7s %7s  %8s %8s %9s" % (
        "architecture", "params", "AUPRC", "F1", "FL rec", "FL F1", "FL AUPRC",
        "cold ms", "stdy ms", "train s"))
    order = [T.ARCH_RESNET50, T.ARCH_MULTISCALE, T.ARCH_MULTILVL_ATTENTION,
             T.ARCH_INCEPTION_ATTENTION, T.ARCH_INCEPTION_REFINE]
    for arch in order:
        r = results[arch]
        j = T.LP_TAGS.index("P1_FL")
        ti = r["timing"]
        print("%-30s %11d %7.5f %7.5f %7.3f %7.3f %7.3f  %8.3f %8.3f %9.1f" % (
            arch, r["m"]["params_total"], r["tm"]["macro_auprc"], r["tm"]["macro_f1"],
            r["rec"][j], r["f1"][j], r["aps"][j],
            ti["inference_ms_per_image_cold"], ti["inference_ms_per_image_steady_median"],
            ti["train_seconds_total"]))
    print("\n=== per-class F1 ===")
    print("%-30s %8s %8s %8s %8s %8s" % ("architecture", *T.LP_TAGS))
    for arch in order:
        r = results[arch]
        print("%-30s %8.3f %8.3f %8.3f %8.3f %8.3f" % (
            arch, *[r["f1"][T.LP_TAGS.index(t)] for t in T.LP_TAGS]))
    print("\n=== per-class recall ===")
    print("%-30s %8s %8s %8s %8s %8s" % ("architecture", *T.LP_TAGS))
    for arch in order:
        r = results[arch]
        print("%-30s %8.3f %8.3f %8.3f %8.3f %8.3f" % (
            arch, *[r["rec"][T.LP_TAGS.index(t)] for t in T.LP_TAGS]))

    base = results[T.ARCH_RESNET50]
    print("\n=== Folded Lens against the plain ResNet50 control of this session ===")
    j = T.LP_TAGS.index("P1_FL")
    for arch in order[1:]:
        r = results[arch]
        print("%-30s FL recall %+.4f (%.3f -> %.3f), FL AUPRC %+.4f, FL F1 %+.4f | macro AUPRC %+.5f, macro F1 %+.5f, exact match %+.5f" % (
            arch,
            r["rec"][j] - base["rec"][j], base["rec"][j], r["rec"][j],
            r["aps"][j] - base["aps"][j], r["f1"][j] - base["f1"][j],
            r["tm"]["macro_auprc"] - base["tm"]["macro_auprc"],
            r["tm"]["macro_f1"] - base["tm"]["macro_f1"],
            r["tm"]["exact_match_ratio"] - base["tm"]["exact_match_ratio"]))

    if BASE_20260928.is_file():
        old = json.loads(BASE_20260928.read_text(encoding="utf-8"))["test_metrics"]
        print("\n=== control re-run against the 2026-09-28 base run (same recipe, same split) ===")
        print("macro AUPRC  %.5f (2026-09-28) vs %.5f (this sweep), delta %+.5f"
              % (old["macro_auprc"], base["tm"]["macro_auprc"], base["tm"]["macro_auprc"] - old["macro_auprc"]))
        print("macro F1     %.5f vs %.5f, delta %+.5f"
              % (old["macro_f1"], base["tm"]["macro_f1"], base["tm"]["macro_f1"] - old["macro_f1"]))
        print("exact match  %.5f vs %.5f, delta %+.5f"
              % (old["exact_match_ratio"], base["tm"]["exact_match_ratio"],
                 base["tm"]["exact_match_ratio"] - old["exact_match_ratio"]))
        print("FL recall    %.5f vs %.5f, FL F1 %.5f vs %.5f"
              % (old["per_class"]["P1_FL"]["recall"], base["tm"]["per_class"]["P1_FL"]["recall"],
                 old["per_class"]["P1_FL"]["f1"], base["tm"]["per_class"]["P1_FL"]["f1"]))

failed = [n for n, ok, _ in checks if not ok]
if failed:
    print("\nFAILED: %s" % failed)
sys.exit(1 if failed else 0)
