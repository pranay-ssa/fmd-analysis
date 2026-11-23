"""Load the frozen 17-class test results into one dictionary for the workbook.

The numbers in the workbook come from this module only. It reads the copied
metrics, thresholds and saved test scores, recomputes AUROC from those scores,
and rechecks the exclusion counts against the frozen store. No torch import.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
RUN_DIR = HERE.parent / "runs" / "20261119_resnet50_224_seed42"
RESULTS_DIR = RUN_DIR / "results"
SPLIT_DIR = HERE.parents[1] / "splits" / "frozen_70_15_15_20261119"
STORE_DIR = HERE.parents[3] / "run" / "frozen_eda_20261117" / "store"

GROUP_ORDER = ["Lens presentation tags", "OOI tags", "OOI tags with Size tag"]

GROUP_BY_CODE = {
    "P1_MPP": "Lens presentation tags",
    "P1_ML": "Lens presentation tags",
    "P2_LOC": "Lens presentation tags",
    "P2_DC": "Lens presentation tags",
    "P1_NL": "Lens presentation tags",
    "P1_FL": "Lens presentation tags",
    "P2_LD": "Lens presentation tags",
    "P1_COC": "Lens presentation tags",
    "P2_FOV": "Lens presentation tags",
    "P1_PPM": "Lens presentation tags",
    "class_bubble": "OOI tags",
    "class_bubble_cluster": "OOI tags",
    "class_wet_package": "OOI tags",
    "class_foreign_matter": "OOI tags with Size tag",
    "class_fiber": "OOI tags with Size tag",
    "class_hema": "OOI tags with Size tag",
    "class_extraneous_polymer": "OOI tags with Size tag",
}

CODE_ORDER = [
    "P1_MPP",
    "P1_ML",
    "P2_LOC",
    "P2_DC",
    "P1_NL",
    "P1_FL",
    "P2_LD",
    "P1_COC",
    "P2_FOV",
    "P1_PPM",
    "class_bubble",
    "class_bubble_cluster",
    "class_wet_package",
    "class_foreign_matter",
    "class_fiber",
    "class_hema",
    "class_extraneous_polymer",
]

# Reader order: the classes that can appear in a pass picture come first. Bubble
# passes alone; the four size-tagged OOI tags pass only when untagged. The rest
# are fail classes. The group blocks stay contiguous so the reader sees each
# group name once.
PASS_ORDER = [
    "class_bubble",
    "class_foreign_matter",
    "class_fiber",
    "class_hema",
    "class_extraneous_polymer",
]
READER_ORDER = PASS_ORDER + [
    "P1_MPP",
    "P1_ML",
    "P2_LOC",
    "P2_DC",
    "P1_NL",
    "P1_FL",
    "P2_LD",
    "P1_COC",
    "P2_FOV",
    "P1_PPM",
    "class_bubble_cluster",
    "class_wet_package",
]

PASS_CLASS = {
    "class_bubble": "Pass",
    "class_foreign_matter": "Pass if untagged",
    "class_fiber": "Pass if untagged",
    "class_hema": "Pass if untagged",
    "class_extraneous_polymer": "Pass if untagged",
}

GATED_CLASSES = [
    "class_foreign_matter",
    "class_fiber",
    "class_extraneous_polymer",
    "class_hema",
]

GATE_BY_CLASS = {
    "class_foreign_matter": "gate_foreign_matter",
    "class_fiber": "gate_fiber",
    "class_extraneous_polymer": "gate_extraneous_polymer",
    "class_hema": "gate_hema",
}

EXCLUDED_ORDER = ["P1_EBC", "P1_LR", "P1_TL", "P2_BSC", "P2_DS", "P1_SG"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(value: float, digits: int = 6) -> float:
    return float(round(float(value), digits))


def pass_fail_verdicts(columns, y_true, y_score, gate, gated, cut: float = 0.5):
    """Return one truth and one predicted verdict per test picture."""
    idx = {c: i for i, c in enumerate(columns)}
    gidx = {g: i for i, g in enumerate(gated)}
    gate_class = {g: "class_" + g[len("gate_"):] for g in gated}
    lens = [c for c in columns if not c.startswith("class_")]

    def truth_fail(i: int) -> bool:
        if any(y_true[i, idx[c]] >= 0.5 for c in lens):
            return True
        if y_true[i, idx["class_bubble_cluster"]] >= 0.5:
            return True
        if y_true[i, idx["class_wet_package"]] >= 0.5:
            return True
        return any(
            y_true[i, idx[gate_class[g]]] >= 0.5 and gate[i, gidx[g]] == 1
            for g in gated
        )

    def pred_fail(i: int) -> bool:
        if any(y_score[i, idx[c]] >= cut for c in lens):
            return True
        if y_score[i, idx["class_bubble_cluster"]] >= cut:
            return True
        if y_score[i, idx["class_wet_package"]] >= cut:
            return True
        return any(y_score[i, idx[gate_class[g]]] >= cut for g in gated)

    actual = np.array([truth_fail(i) for i in range(len(y_true))], dtype=bool)
    predicted = np.array([pred_fail(i) for i in range(len(y_score))], dtype=bool)
    return actual, predicted


def compute_pass_fail(columns, y_true, y_score, gate, gated, per_class, cut: float = 0.5, verdicts=None) -> dict:
    """One pass/fail verdict per test picture under the agreed rule.

    Truth fails on any lens presentation tag, Bubble Cluster, Wet Package, or a
    size-gated class whose size tag is set. Bubble alone passes. Clear is outside
    this experiment.

    The model has no size output, so a predicted size-gated class counts as a
    predicted fail; the size tag changes only the truth.
    """
    idx = {c: i for i, c in enumerate(columns)}
    gidx = {g: i for i, g in enumerate(gated)}
    gate_class = {g: "class_" + g[len("gate_"):] for g in gated}
    lens = [c for c in columns if not c.startswith("class_")]

    actual, predicted = verdicts if verdicts is not None else pass_fail_verdicts(
        columns, y_true, y_score, gate, gated, cut
    )

    ta = int(((~actual) & (~predicted)).sum())
    fr = int(((~actual) & predicted).sum())
    tr = int((actual & predicted).sum())
    fa = int((actual & (~predicted)).sum())
    actual_pass = int((~actual).sum())
    actual_fail = int(actual.sum())
    predicted_pass = int((~predicted).sum())
    predicted_fail = int(predicted.sum())
    n = len(actual)
    if ta + fr + tr + fa != n:
        raise ValueError("pass/fail counts do not add to the test set")
    if ta + fr != actual_pass or fa + tr != actual_fail:
        raise ValueError("pass/fail counts do not add to actual verdicts")
    if ta + fa != predicted_pass or fr + tr != predicted_fail:
        raise ValueError("pass/fail counts do not add to predicted verdicts")

    cause_rows = [
        (
            "Any lens presentation tag",
            sum(1 for i in range(n) if actual[i] and any(y_true[i, idx[c]] >= 0.5 for c in lens)),
            sum(1 for i in range(n) if predicted[i] and any(y_score[i, idx[c]] >= cut for c in lens)),
        ),
        (
            "Bubble Cluster",
            sum(1 for i in range(n) if actual[i] and y_true[i, idx["class_bubble_cluster"]] >= 0.5),
            sum(1 for i in range(n) if predicted[i] and y_score[i, idx["class_bubble_cluster"]] >= cut),
        ),
        (
            "Wet Package",
            sum(1 for i in range(n) if actual[i] and y_true[i, idx["class_wet_package"]] >= 0.5),
            sum(1 for i in range(n) if predicted[i] and y_score[i, idx["class_wet_package"]] >= cut),
        ),
    ]
    for g in gated:
        c = gate_class[g]
        name = per_class[c]["name"]
        cause_rows.append(
            (
                f"{name}, size tag",
                sum(
                    1
                    for i in range(n)
                    if actual[i] and y_true[i, idx[c]] >= 0.5 and gate[i, gidx[g]] == 1
                ),
                sum(1 for i in range(n) if predicted[i] and y_score[i, idx[c]] >= cut),
            )
        )

    return {
        "cut": cut,
        "TA": ta,
        "FR": fr,
        "TR": tr,
        "FA": fa,
        "actual_pass": actual_pass,
        "actual_fail": actual_fail,
        "predicted_pass": predicted_pass,
        "predicted_fail": predicted_fail,
        "tar": ta / (ta + fr) if ta + fr else float("nan"),
        "trr": tr / (tr + fa) if tr + fa else float("nan"),
        "far": fa / (tr + fa) if tr + fa else float("nan"),
        "frr": fr / (ta + fr) if ta + fr else float("nan"),
        "causes": [
            {"label": label, "actual": actual_n, "predicted": predicted_n}
            for label, actual_n, predicted_n in cause_rows
        ],
    }



def compute_pass_images(columns, y_true, y_score, per_class, actual, predicted):
    """Summarise the truth-pass pictures by class and by exact class set."""
    idx = {c: i for i, c in enumerate(columns)}

    by_class = []
    for code in CODE_ORDER:
        present = y_true[:, idx[code]] >= 0.5
        pictures = int((present & ~actual).sum())
        predicted_pass = int((present & ~actual & ~predicted).sum())
        by_class.append(
            {
                "code": code,
                "name": per_class[code]["name"],
                "pass_class": PASS_CLASS.get(code, "Fail"),
                "pictures": pictures,
                "predicted_pass": predicted_pass,
                "predicted_fail": pictures - predicted_pass,
            }
        )

    groups: dict[tuple[str, ...], dict] = {}
    for i in range(len(y_true)):
        if actual[i]:
            continue
        present = tuple(c for c in PASS_ORDER if y_true[i, idx[c]] >= 0.5)
        key = present
        entry = groups.setdefault(
            key,
            {
                "codes": list(key),
                "label": (
                    f"{per_class[key[0]]['name']} only"
                    if len(key) == 1
                    else " + ".join(per_class[c]["name"] for c in key)
                )
                if key
                else "No class label",
                "pictures": 0,
                "predicted_pass": 0,
                "predicted_fail": 0,
            },
        )
        entry["pictures"] += 1
        if predicted[i]:
            entry["predicted_fail"] += 1
        else:
            entry["predicted_pass"] += 1

    by_set = sorted(groups.values(), key=lambda item: (-item["pictures"], item["label"]))
    total = int((~actual).sum())
    predicted_pass = int((~actual & ~predicted).sum())
    predicted_fail = int((~actual & predicted).sum())
    if sum(item["pictures"] for item in by_set) != total:
        raise ValueError("pass-image sets do not add to the pass total")
    if predicted_pass + predicted_fail != total:
        raise ValueError("pass-image predictions do not add to the pass total")
    return {
        "by_class": by_class,
        "by_set": by_set,
        "total": total,
        "predicted_pass": predicted_pass,
        "predicted_fail": predicted_fail,
    }


def load_data() -> dict:
    metrics = json.loads((RESULTS_DIR / "metrics.json").read_text(encoding="utf-8"))
    meta = json.loads((SPLIT_DIR / "meta.json").read_text(encoding="utf-8"))
    pred = np.load(RESULTS_DIR / "predictions.npz", allow_pickle=False)
    rule_all = metrics["thresholds"]

    columns = [str(c) for c in pred["columns"].tolist()]
    y_true = pred["test_true"]
    y_score = pred["test_score"]
    test_pictures = int(y_true.shape[0])
    positive_labels = int(y_true.sum())

    if test_pictures != int(metrics["rows"]):
        raise ValueError(f"test pictures {test_pictures} != metrics rows {metrics['rows']}")
    if len(columns) != 17:
        raise ValueError(f"expected 17 columns, got {len(columns)}")
    if set(columns) != set(CODE_ORDER):
        raise ValueError("column set does not match the workbook order")

    per_class = metrics["per_class"]
    rows: list[dict] = []
    for code in CODE_ORDER:
        index = columns.index(code)
        item = per_class[code]
        support = int(item["support"])
        truth = y_true[:, index]
        if int(truth.sum()) != support:
            raise ValueError(f"{code}: support {support} != truth {int(truth.sum())}")
        auc = float(roc_auc_score(truth, y_score[:, index]))
        cut = float(item["threshold"])
        rule = rule_all["per_class"][code]
        at_cut = next(
            (point for point in rule["curve"] if abs(float(point["threshold"]) - cut) < 1e-9),
            None,
        )
        if at_cut is None:
            raise ValueError(f"{code}: no validation curve point at cut {cut}")

        rows.append(
            {
                "code": code,
                "name": item["name"],
                "group": GROUP_BY_CODE[code],
                "pass_class": PASS_CLASS.get(code, "Fail"),
                "support": support,
                "prevalence": support / test_pictures,
                "auroc": auc,
                "auprc": float(item["auprc"]),
                "cut": cut,
                "cut_source": rule.get("source", ""),
                "cut_reason": rule.get("reason", ""),
                "val_support": int(rule.get("val_support") or 0),
                "val_precision_at_cut": float(at_cut["precision"]),
                "val_recall_at_cut": float(at_cut["recall"]),
                "val_f1_at_cut": float(at_cut["f1"]),
                "precision_05": float(item["precision_0.5"]),
                "recall_05": float(item["recall_0.5"]),
                "f1_05": float(item["f1_0.5"]),
                "ta_05": int(item["tn_0.5"]),
                "fr_05": int(item["fp_0.5"]),
                "tr_05": int(item["tp_0.5"]),
                "fa_05": int(item["fn_0.5"]),
                "tp_05": int(item["tp_0.5"]),
                "fp_05": int(item["fp_0.5"]),
                "fn_05": int(item["fn_0.5"]),
                "tn_05": int(item["tn_0.5"]),
                "precision_chosen": float(item["precision_chosen"]),
                "recall_chosen": float(item["recall_chosen"]),
                "f1_chosen": float(item["f1_chosen"]),
                "ta_chosen": int(item["tn_chosen"]),
                "fr_chosen": int(item["fp_chosen"]),
                "tr_chosen": int(item["tp_chosen"]),
                "fa_chosen": int(item["fn_chosen"]),
                "tp_chosen": int(item["tp_chosen"]),
                "fp_chosen": int(item["fp_chosen"]),
                "fn_chosen": int(item["fn_chosen"]),
                "tn_chosen": int(item["tn_chosen"]),
            }
        )

    macro = {
        "auroc": float(np.mean([r["auroc"] for r in rows])),
        "auprc": float(np.mean([r["auprc"] for r in rows])),
        "precision_05": float(np.mean([r["precision_05"] for r in rows])),
        "recall_05": float(np.mean([r["recall_05"] for r in rows])),
        "f1_05": float(np.mean([r["f1_05"] for r in rows])),
        "precision_chosen": float(np.mean([r["precision_chosen"] for r in rows])),
        "recall_chosen": float(np.mean([r["recall_chosen"] for r in rows])),
        "f1_chosen": float(np.mean([r["f1_chosen"] for r in rows])),
    }
    for key, reported in (
        ("auprc", metrics["macro_auprc"]),
        ("f1_05", metrics["macro_f1_0.5"]),
        ("f1_chosen", metrics["macro_f1_chosen"]),
    ):
        if abs(macro[key] - float(reported)) > 1e-9:
            raise ValueError(f"macro {key} {macro[key]} != reported {reported}")
    if int(sum(r["support"] for r in rows)) != positive_labels:
        raise ValueError("sum of supports != positive labels")

    gated = [str(c) for c in pred["gated_columns"]]
    verdicts = pass_fail_verdicts(
        columns, y_true, y_score, pred["test_gate"], gated
    )
    pass_fail = compute_pass_fail(
        columns, y_true, y_score, pred["test_gate"], gated, per_class, verdicts=verdicts
    )
    pass_images = compute_pass_images(
        columns, y_true, y_score, per_class, verdicts[0], verdicts[1]
    )

    split_rows = _read_csv(SPLIT_DIR / "labels_17.csv")
    keys = {row["md5"] for row in split_rows}
    model_columns = [c for c in split_rows[0] if c not in ("md5", "image_path", "split")]
    if len(model_columns) != 17:
        raise ValueError(f"expected 17 model columns, got {len(model_columns)}")

    gate_rows = {row["md5"]: row for row in _read_csv(SPLIT_DIR / "gates_4.csv")}
    if set(gate_rows) != keys:
        raise ValueError("gate table md5s do not match the label table")

    tag_rows = _read_csv(STORE_DIR / "labels" / "tags.csv")
    box_rows = _read_csv(STORE_DIR / "labels" / "boxes.csv")

    tag_pictures = {code: set() for code in EXCLUDED_ORDER}
    tag_instances = {code: 0 for code in EXCLUDED_ORDER}
    box_pictures = {code: set() for code in EXCLUDED_ORDER}
    for row in tag_rows:
        code = row["code"]
        if code in tag_pictures and row["picture_key"] in keys:
            tag_pictures[code].add(row["picture_key"])
            tag_instances[code] += int(float(row.get("instances") or 1))
    for row in box_rows:
        code = row["code"]
        if code in box_pictures and row["picture_key"] in keys:
            box_pictures[code].add(row["picture_key"])

    excluded = []
    for code in EXCLUDED_ORDER:
        info = meta["excluded_classes"][code]
        pictures = len(tag_pictures[code] | box_pictures[code])
        if pictures != int(info["pictures"]):
            raise ValueError(f"{code}: {pictures} pictures != meta {info['pictures']}")
        excluded.append(
            {
                "code": code,
                "name": info["name"],
                "pictures": pictures,
                "kind": "box" if box_pictures[code] else "tag",
                "annotations": tag_instances[code] if tag_pictures[code] else None,
            }
        )

    excluded_union = set().union(*tag_pictures.values(), *box_pictures.values())
    only_excluded = 0
    for row in split_rows:
        if row["md5"] not in excluded_union:
            continue
        if sum(int(float(row[column] or 0)) for column in model_columns) == 0:
            only_excluded += 1
    if len(excluded_union) != 281:
        raise ValueError(f"excluded union {len(excluded_union)} != 281")
    if only_excluded != 0:
        raise ValueError(f"{only_excluded} pictures carry only excluded classes")

    population = meta["population"]
    if population["records"] - population["duplicate_records_dropped"] != population["distinct_pictures"]:
        raise ValueError("population chain does not add after duplicates")
    if population["distinct_pictures"] - population["unmarked_excluded"] != population["rows"] + population["clear_excluded"]:
        raise ValueError("population chain does not add after Clear")
    split_counts = meta["split_counts"]
    if sum(split_counts.values()) != population["rows"]:
        raise ValueError("split counts do not add to the analysed rows")

    split_order = ("train", "val", "test")
    class_split_rows = []
    for code in CODE_ORDER:
        counts = {
            split: sum(
                1
                for row in split_rows
                if row["split"] == split and int(float(row[code] or 0)) == 1
            )
            for split in split_order
        }
        if counts["test"] != int(per_class[code]["support"]):
            raise ValueError(f"{code}: split test count != test support")
        class_split_rows.append(
            {
                "code": code,
                "name": per_class[code]["name"],
                "group": GROUP_BY_CODE[code],
                "train": counts["train"],
                "val": counts["val"],
                "test": counts["test"],
                "total": counts["train"] + counts["val"] + counts["test"],
            }
        )

    size_split_rows = []
    for code in GATED_CLASSES:
        gate_column = GATE_BY_CLASS[code]
        item = {"code": code, "name": per_class[code]["name"]}
        for split in split_order:
            pictures = [
                row
                for row in split_rows
                if row["split"] == split and int(float(row[code] or 0)) == 1
            ]
            tagged = sum(
                1 for row in pictures if int(float(gate_rows[row["md5"]][gate_column] or 0)) == 1
            )
            item[f"{split}_total"] = len(pictures)
            item[f"{split}_tagged"] = tagged
            item[f"{split}_untagged"] = len(pictures) - tagged
        size_split_rows.append(item)

    threshold_rule = {
        "objective": rule_all.get("objective", ""),
        "grid": rule_all.get("grid", []),
        "min_val_positives": int(rule_all.get("min_val_positives", 0)),
        "default_threshold": float(rule_all.get("default_threshold", 0.5)),
        "seeds": 1,
        "n_default": len(rule_all.get("default", [])),
    }

    config = metrics["config"]
    timing = metrics["timing"]
    rows_by_code = {row["code"]: row for row in rows}
    reader_rows = [rows_by_code[code] for code in READER_ORDER]

    return {
        "test_pictures": test_pictures,
        "positive_labels": positive_labels,
        "rows": rows,
        "reader_rows": reader_rows,
        "macro": macro,
        "pass_fail": pass_fail,
        "pass_images": pass_images,
        "class_split": class_split_rows,
        "size_split": size_split_rows,
        "excluded": excluded,
        "excluded_union": len(excluded_union),
        "excluded_only": only_excluded,
        "p1_lr_annotations": next(
            (row["annotations"] for row in excluded if row["code"] == "P1_LR"), None
        ),
        "clear": int(population["clear_excluded"]),
        "duplicates": int(population["duplicate_records_dropped"]),
        "unmarked": int(population["unmarked_excluded"]),
        "records": int(population["records"]),
        "distinct": int(population["distinct_pictures"]),
        "labelled": int(population["rows"] + population["clear_excluded"]),
        "analysed": int(population["rows"]),
        "splits": {
            "train": int(split_counts["train"]),
            "val": int(split_counts["val"]),
            "test": int(split_counts["test"]),
        },
        "threshold_rule": threshold_rule,
        "timing": {
            "seconds_total": float(timing["seconds_total"]),
            "seconds_training": float(timing["seconds_training"]),
            "seconds_per_epoch": float(timing["seconds_per_epoch"]),
            "seconds_inference": float(timing["seconds_inference"]),
            "inference_images": int(timing["inference_images"]),
            "inference_ms_per_image": float(timing["inference_ms_per_image"]),
        },
        "model": {
            "arch": "ResNet50" if config["arch"].lower() == "resnet50" else config["arch"],
            "imgsz": int(config["imgsz"]),
            "batch": int(config["batch"]),
            "epochs": int(config["epochs"]),
            "lr": float(config["lr"]),
            "seed": int(config["seed"]),
            "pos_weight": config["pos_weight"],
            "split_shape": config["split_shape"],
        },
    }


if __name__ == "__main__":
    data = load_data()
    print(json.dumps({k: data[k] for k in ("test_pictures", "positive_labels", "macro", "threshold_rule")}, indent=2))
    print()
    for row in data["rows"]:
        print(
            f"{row['code']:26s} {row['group']:24s} support={row['support']:4d} "
            f"auroc={row['auroc']:.4f} auprc={row['auprc']:.4f} "
            f"P={row['precision_05']*100:5.1f} R={row['recall_05']*100:5.1f} F1={row['f1_05']*100:5.1f} "
            f"cut={row['cut']:.2f} val_n={row['val_support']}"
        )
    print()
    print("excluded:", data["excluded"])
    print("excluded union:", data["excluded_union"], "only excluded:", data["excluded_only"])
    print("P1_LR annotations:", data["p1_lr_annotations"])
