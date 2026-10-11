#!/usr/bin/env python3
"""Unit tests for experiments/cnn/dump_outputs.py (no tensorflow needed).

Run:  python tests/test_dump_outputs.py      (or pytest tests/test_dump_outputs.py)
"""
import csv
import importlib.util
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load():
    path = os.path.join(REPO, "experiments", "cnn", "dump_outputs.py")
    spec = importlib.util.spec_from_file_location("dump_outputs", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_file_paths_order():
    mod = load()
    root = tempfile.mkdtemp()
    try:
        for cls, files in (("B_cls", ["z.bmp", "a.bmp"]),
                           ("A_cls", ["2.bmp", "1.bmp"])):
            os.makedirs(os.path.join(root, cls))
            for f in files:
                open(os.path.join(root, cls, f), "wb").close()
        paths, labels = mod.test_file_paths(root, ["A_cls", "B_cls"])
        got = [(os.path.basename(os.path.dirname(p)), os.path.basename(p),
                l) for p, l in zip(paths, labels)]
        assert got == [("A_cls", "1.bmp", 0), ("A_cls", "2.bmp", 0),
                       ("B_cls", "a.bmp", 1), ("B_cls", "z.bmp", 1)], got
    finally:
        shutil.rmtree(root)


def test_dump_outputs_writes_both_files():
    mod = load()
    out = tempfile.mkdtemp()
    try:
        classes = ["Clear", "Bubble", "Fiber"]
        y_true = [0, 1, 1, 2]
        y_pred = [0, 1, 2, 1]
        y_prob = [[0.9, 0.05, 0.05],
                  [0.1, 0.8, 0.1],
                  [0.2, 0.3, 0.5],
                  [0.2, 0.7, 0.1]]
        files = ["x/a.bmp", "x/b.bmp", "x/c.bmp", "x/d.bmp"]
        p_csv, c_json = mod.dump_outputs(out, classes, y_true, y_pred, y_prob,
                                         file_paths=files)

        rows = list(csv.DictReader(open(p_csv, newline="", encoding="utf-8")))
        assert len(rows) == 4, len(rows)
        assert rows[1]["true"] == "Bubble" and rows[1]["pred"] == "Bubble"
        assert rows[2]["pred"] == "Fiber"
        assert float(rows[3]["p_Bubble"]) == 0.7
        assert rows[0]["file"] == "x/a.bmp"

        conf = json.load(open(c_json, encoding="utf-8"))
        assert conf["class_names"] == classes
        # rows = true, cols = pred: (true Fiber, pred Bubble) == 1
        m = conf["matrix"]
        assert m[2][1] == 1, m
        assert m[1][1] == 1 and m[1][2] == 1 and m[0][0] == 1, m
        assert sum(sum(r) for r in m) == 4
        assert conf["support"] == [1, 2, 1]
        assert conf["order_match"] is True
    finally:
        shutil.rmtree(out)


def test_length_mismatch_raises():
    mod = load()
    out = tempfile.mkdtemp()
    try:
        try:
            mod.dump_outputs(out, ["a", "b"], [0, 1], [0], [[0.5, 0.5]] * 2)
        except ValueError as e:
            assert "length mismatch" in str(e)
        else:
            raise AssertionError("expected ValueError")
    finally:
        shutil.rmtree(out)


def test_bad_probability_width_raises():
    mod = load()
    out = tempfile.mkdtemp()
    try:
        try:
            mod.dump_outputs(out, ["a", "b"], [0], [1], [[0.3, 0.3, 0.4]])
        except ValueError as e:
            assert "expected 2" in str(e)
        else:
            raise AssertionError("expected ValueError")
    finally:
        shutil.rmtree(out)


def test_missing_file_paths_gives_index_rows():
    mod = load()
    out = tempfile.mkdtemp()
    try:
        p_csv, c_json = mod.dump_outputs(out, ["a", "b"], [0, 1], [1, 1],
                                         [[0.4, 0.6], [0.4, 0.6]],
                                         file_paths=None)
        rows = list(csv.DictReader(open(p_csv, newline="", encoding="utf-8")))
        assert rows[0]["file"] == "" and rows[0]["index"] == "0"
        conf = json.load(open(c_json, encoding="utf-8"))
        assert conf["order_match"] is None
    finally:
        shutil.rmtree(out)


def test_wrong_length_file_paths_falls_back():
    mod = load()
    out = tempfile.mkdtemp()
    try:
        p_csv, c_json = mod.dump_outputs(out, ["a", "b"], [0, 1], [0, 1],
                                         [[0.9, 0.1], [0.1, 0.9]],
                                         file_paths=["only_one.bmp"])
        rows = list(csv.DictReader(open(p_csv, newline="", encoding="utf-8")))
        assert rows[0]["file"] == ""
        conf = json.load(open(c_json, encoding="utf-8"))
        assert conf["order_match"] is False
    finally:
        shutil.rmtree(out)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print("ok   %s" % fn.__name__)
        except Exception as e:              # noqa: BLE001
            failed += 1
            print("FAIL %s: %r" % (fn.__name__, e))
    print("%d tests, %d failed" % (len(fns), failed))
    sys.exit(1 if failed else 0)
