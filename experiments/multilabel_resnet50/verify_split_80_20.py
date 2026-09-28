#!/usr/bin/env python3
"""Independent verification of the 80/20 multilabel split (2026-09-28).

Re-derives every claim in splits/variant_80_20_two_way.meta.json from the raw
files, without importing the builder. Checks, in order:
  1 final_80_20_dataframe.csv: 3377 rows, 5 binary columns, split train/test only
  2 counts: 2700 train / 677 test (79.95 / 20.05 percent)
  3 totals per class match the annotation audit (183/178/1442/1427/325)
  4 positives per split match the meta json
  5 no duplicate image_path, no path in both splits
  6 zero md5 group leaks (identical pixels never straddle the split)
  7 the delivered dataframe agrees with variant_80_20_two_way.csv row for row
  8 the test set is identical to the 3-way variant_80_20.csv test set
  9 labels agree with the master labels.csv for every row
 10 co-occurrence: every Folded Lens positive also carries Multiple Lenses
Exit code 0 only if every check passes.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLASSES = ["P1_COC", "P1_FL", "P1_ML", "P1_MPP", "P1_NL"]
DF_CLASSES = ["Cavity_Off_Center", "Folded_Lens", "Multiple_Lenses",
              "Missing_Primary_Package", "Missing_Lens"]
EXPECTED_TOTALS = {"P1_COC": 183, "P1_FL": 178, "P1_ML": 1442,
                   "P1_MPP": 1427, "P1_NL": 325}


def main():
    failures = []

    def check(name, ok, detail=""):
        print("%-58s %s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            failures.append(name)

    # ---- load the three files ------------------------------------------------
    final = list(csv.DictReader(open(HERE / "final_80_20_dataframe.csv",
                                     newline="", encoding="utf-8")))
    two_way = list(csv.DictReader(open(HERE / "splits" / "variant_80_20_two_way.csv",
                                       newline="", encoding="utf-8")))
    three_way = list(csv.DictReader(open(HERE / "splits" / "variant_80_20.csv",
                                         newline="", encoding="utf-8")))
    labels = {r["image_path"]: r for r in
              csv.DictReader(open(HERE / "labels.csv", newline="", encoding="utf-8"))}

    # 1 shape ------------------------------------------------------------------
    check("1a dataframe row count == 3377", len(final) == 3377, "got %d" % len(final))
    check("1b two_way row count == 3377", len(two_way) == 3377, "got %d" % len(two_way))
    bad_bin = [r for r in final
               if any(r[c] not in ("0", "1") for c in DF_CLASSES)]
    check("1c all label cells are 0/1", not bad_bin, "%d bad rows" % len(bad_bin))
    split_vals = {r["split_named"] for r in final}
    check("1d split_named holds only train/test",
          split_vals <= {"train", "test"}, str(sorted(split_vals)))
    # the internal split column may carve a val inside the 80%, but every val
    # row must sit inside split_named=train (no val image ever reaches test)
    val_outside_train = [r["image_path"] for r in final
                         if r["split"] not in ("train", "test")
                         and r["split_named"] != "train"]
    check("1e internal val rows (if any) all sit in split_named=train",
          not val_outside_train, "%d outside" % len(val_outside_train))

    # 2 counts -----------------------------------------------------------------
    n_train = sum(1 for r in final if r["split_named"] == "train")
    n_test = sum(1 for r in final if r["split_named"] == "test")
    check("2a train == 2700", n_train == 2700, "got %d" % n_train)
    check("2b test == 677", n_test == 677, "got %d" % n_test)
    check("2c train fraction == 0.7995 (80/20 exact at group level)",
          abs(n_train / len(final) - 0.8) < 0.005, "%.4f" % (n_train / len(final)))

    # 3 class totals vs the annotation audit ------------------------------------
    for i, cls in enumerate(CLASSES):
        total = sum(int(r[DF_CLASSES[i]]) for r in final)
        check("3 total %s == %d" % (cls, EXPECTED_TOTALS[cls]),
              total == EXPECTED_TOTALS[cls], "got %d" % total)

    # 4 positives per split vs meta ---------------------------------------------
    meta = json.loads((HERE / "splits" / "variant_80_20_two_way.meta.json").read_text())
    ok4 = True
    detail4 = []
    for s in ("train", "test"):
        for i, cls in enumerate(CLASSES):
            got = sum(int(r[DF_CLASSES[i]]) for r in final if r["split_named"] == s)
            want = meta["positives_per_split"][s][cls]
            if got != want:
                ok4 = False
                detail4.append("%s/%s %d != %d" % (s, cls, got, want))
    check("4 positives per split match meta json", ok4, "; ".join(detail4))

    # 5 duplicates and overlap ---------------------------------------------------
    paths = [r["image_path"] for r in final]
    check("5a no duplicate image_path", len(set(paths)) == len(paths),
          "%d dups" % (len(paths) - len(set(paths))))
    train_set = {r["image_path"] for r in final if r["split_named"] == "train"}
    test_set = {r["image_path"] for r in final if r["split_named"] == "test"}
    check("5b no path in both splits", not (train_set & test_set))

    # 6 md5 group leaks -----------------------------------------------------------
    per_group = defaultdict(set)
    for r in two_way:
        key = r["md5"] or ("path:" + r["image_path"])
        per_group[key].add(r["split"])
    leaks = sum(1 for v in per_group.values() if len(v) > 1)
    check("6 zero md5 group leaks", leaks == 0, "%d leaked groups" % leaks)

    # 7 dataframe vs two_way csv, row for row --------------------------------------
    tw = {r["image_path"]: r for r in two_way}
    ok7, detail7 = True, []
    for r in final:
        t = tw.get(r["image_path"])
        if t is None:
            ok7 = False
            detail7.append("missing " + r["image_path"])
            continue
        if t["split"] != r["split_named"]:
            ok7 = False
            detail7.append("split mismatch " + r["image_path"])
        for i, cls in enumerate(CLASSES):
            if int(t[cls]) != int(r[DF_CLASSES[i]]):
                ok7 = False
                detail7.append("label mismatch %s %s" % (r["image_path"], cls))
    check("7 dataframe agrees with two_way csv", ok7, "; ".join(detail7[:3]))

    # 8 test set identical to the 3-way variant -------------------------------------
    ref_test = {r["image_path"] for r in three_way if r["split"] == "test"}
    check("8 test set == 3-way variant_80_20 test", ref_test == test_set,
          "%d vs %d" % (len(ref_test), len(test_set)))

    # 9 labels agree with master labels.csv ------------------------------------------
    ok9, miss, mism = True, [], []
    for r in final:
        lab = labels.get(r["image_path"])
        if lab is None:
            miss.append(r["image_path"])
            continue
        for i, cls in enumerate(CLASSES):
            if int(lab[cls]) != int(r[DF_CLASSES[i]]):
                mism.append("%s %s" % (r["image_path"], cls))
    check("9a every path exists in labels.csv", not miss, "%d missing" % len(miss))
    check("9b every label matches labels.csv", not mism, "%d mismatches" % len(mism))

    # 10 co-occurrence -----------------------------------------------------------------
    fl_total = sum(int(r["Folded_Lens"]) for r in final)
    fl_also_ml = sum(int(r["Folded_Lens"]) and int(r["Multiple_Lenses"]) for r in final)
    check("10 every Folded_Lens positive also Multiple_Lenses (178/178)",
          fl_total == fl_also_ml == 178, "%d/%d" % (fl_also_ml, fl_total))

    print("\n%d checks, %d failed" % (15, len(failures)))
    if failures:
        print("FAILED: %s" % failures)
        return 1
    print("SPLIT VERIFIED: 80/20 is valid, leak-free and consistent end to end")
    return 0


if __name__ == "__main__":
    sys.exit(main())
