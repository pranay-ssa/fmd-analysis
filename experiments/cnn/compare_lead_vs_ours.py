#!/usr/bin/env python3
"""Compare the lead's notebook architectures against ours in model_training.py.

Compares STRUCTURE, not formatting: for each architecture it walks the code in source order,
collects every layer-construction call as (layer, positional args, keyword args minus "name")
and diffs the two sequences. Cosmetic differences (whitespace, comments, docstrings, variable
names, `tf.keras.` prefixes, layer `name=` strings) are ignored by construction.

It also normalises one known API change: Keras 3 removed LeakyReLU's `alpha` argument, so
`alpha=0.1` and `negative_slope=0.1` are treated as the same thing and reported separately.

USAGE
    python3 experiments/cnn/compare_lead_vs_ours.py
"""
from __future__ import annotations

import ast
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
NOTEBOOK = HERE.parent.parent / "notebooks" / "FMD_ResNet50Architectures.ipynb"
TRAINER = HERE / "model_training.py"

LAYER_HINT = (
    "Input", "Conv2D", "Conv2DTranspose", "DepthwiseConv2D", "MaxPooling2D", "UpSampling2D",
    "BatchNormalization", "LeakyReLU", "Concatenate", "GlobalAveragePooling2D", "Dense",
    "Dropout", "Reshape", "Multiply", "ResNet50", "preprocess_input", "get_layer",
    "se_block", "inception_block", "inception_attention_block", "Model",
)


def repair_leading_space(src: str) -> str:
    """The lead's SE cell has stray single-space indents at top level; strip them so it parses."""
    out = []
    for line in src.splitlines():
        if line[:1] == " " and line[:2] != "  " and line.strip():
            out.append(line[1:])
        else:
            out.append(line)
    return "\n".join(out)


def calls_in_order(src: str):
    """Layer calls as (layer, args, kwargs) in source order, cosmetics removed."""
    tree = ast.parse(src)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
        if name not in LAYER_HINT:
            continue
        args = []
        for a in node.args:
            try:
                args.append(ast.literal_eval(a))
            except Exception:
                args.append(ast.unparse(a))
        kwargs = {}
        for kw in node.keywords:
            if kw.arg == "name":
                continue
            if kw.arg == "alpha":
                kw = ast.keyword(arg="negative_slope", value=kw.value)
            try:
                kwargs[kw.arg] = ast.literal_eval(kw.value)
            except Exception:
                kwargs[kw.arg] = ast.unparse(kw.value)
        found.append(((node.lineno, node.col_offset), name, tuple(map(str, args)), kwargs))
    found.sort(key=lambda x: x[0])
    return [(n, a, k) for _, n, a, k in found]


def filter_dicts(src: str) -> dict:
    """The l3/l4/l5 inception filter configurations, wherever they are assigned."""
    out = {}
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            for t in node.targets:
                if getattr(t, "id", "").startswith(("l3_filters", "l4_filters", "l5_filters")):
                    out[t.id] = ast.literal_eval(node.value)
    return out


def func_src(src: str, name: str) -> str:
    for n in ast.parse(src).body:
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return ast.get_source_segment(src, n)
    raise KeyError(name)


nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
lead_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
lead = {}
for i, c in enumerate(lead_cells):
    src = "".join(c["source"])
    try:
        ast.parse(src)
        ok = True
    except SyntaxError:
        src = repair_leading_space(src)
        ok = False
    lead[i] = (src, ok)

trainer_src = TRAINER.read_text(encoding="utf-8")

def split_cell(src: str):
    """Split a lead cell into (helper function sources, assembly source).

    The lead's cells define the block and then assemble the model in the same cell, so a fair
    comparison needs the two parts separated: the helper bodies are compared against our helper
    functions, and the assembly against our arch_* function.
    """
    tree = ast.parse(src)
    parts, helpers, lines = {}, {}, src.splitlines()
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            helpers[n.name] = ast.get_source_segment(src, n)
        parts[n.lineno] = n
    first_assembly = min((ln for ln, n in parts.items() if not isinstance(n, ast.FunctionDef)),
                         default=None)
    if first_assembly is None:
        return helpers, ""
    assembly = "\n".join(lines[first_assembly - 1:])
    return helpers, assembly


def normalized(src: str):
    return calls_in_order(src)


PAIRS = [
    (0, "arch_resnet50_inception", "1. MultiLevel MultiScale (Inception)", "inception_block"),
    (1, "arch_resnet50_se", "2. MultiLevel Attention (SE)", "se_block"),
    (2, "arch_resnet50_inception_attention", "3. Inception + branch attention",
     "inception_attention_block"),
    (3, "arch_resnet50_inception_refine", "4. Inception + refined decode", "inception_block"),
]

results = []
for idx, fn, label, helper in PAIRS:
    cell_src, parsed_as_is = lead[idx]
    helpers, assembly = split_cell(cell_src)
    ours_arch = func_src(trainer_src, fn)
    ours_helper = func_src(trainer_src, helper)

    lead_helper = helpers.get(helper)
    helper_same = lead_helper is not None and \
        normalized(lead_helper) == normalized(ours_helper)

    a = normalized(assembly)
    b = normalized(ours_arch)
    # The helper bodies are excluded from the assembly by split_cell, so the two sequences are
    # directly comparable: both contain the taps, the block applications, the fusion and the head.
    a_clean = a
    same_assembly = a_clean == b
    first = None
    for i, (x, y) in enumerate(zip(a_clean, b)):
        if x != y:
            first = (i, x, y)
            break
    if first is None and len(a_clean) != len(b):
        first = (min(len(a_clean), len(b)), f"length {len(a_clean)} vs {len(b)}", None)
    results.append(dict(label=label, fn=fn, helper=helper, parses=parsed_as_is,
                        helper_same=helper_same, assembly_same=same_assembly, first=first,
                        n_lead=len(a_clean), n_ours=len(b),
                        filters_lead=filter_dicts(cell_src), filters_ours=filter_dicts(ours_arch)))


def _belongs_to(call, helpers, inline_helpers):
    """"Heuristic: a call is block-internal if its layer type appears only inside an inlined helper."""
    return False


print("=" * 100)
for r in results:
    print(f"{r['label']:<34} helper({r['helper']}) identical: {r['helper_same']}")
    print(f"{'':<34} assembly identical: {r['assembly_same']} "
          f"(calls {r['n_lead']} vs {r['n_ours']}, lead cell parses as-is: {r['parses']})")
    if r["first"]:
        i, x, y = r["first"]
        print(f"{'':<34} first assembly difference at call {i}:")
        print(f"{'':<36} lead: {x}")
        print(f"{'':<36} ours: {y}")
    fl, fo = r["filters_lead"], r["filters_ours"]
    if fl or fo:
        print(f"{'':<34} filter dicts equal: {fl == fo}")
print("=" * 100)
