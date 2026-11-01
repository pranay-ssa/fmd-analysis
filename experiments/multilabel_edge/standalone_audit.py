"""Standalone-tag audit (ticket 023): P1_MPP, P1_PPM, P1_COC, P2_FOV/F2_FOV.

The Draft 2 guide (sections 4.1 to 4.4) says each of these tags is standalone:
when it is assigned, no additional tags or labels apply to the picture.

Two independent derivations, then a comparison:
  A. resolved line: run/eda_full_20261015/resolved_labels.csv (per-shape,
     one winning source per picture).
  B. raw line: the newer annotation XMLs parsed directly
     (Updated Annotations 20260922.xml + annotations_452194*.xml), every
     source counted, names joined to content md5 via file_manifest.csv.

Gate tags (P3_*_MICRON_THRESHOLD) are size flags, not extra labels; they are
counted in their own column.
Output: run/multilabel_edge_20261023/standalone_audit.json + violation list CSV.
"""
import csv, json, collections, glob, os
import xml.etree.ElementTree as ET

ROOT = "D:/fmd-analysis"
EDA = f"{ROOT}/run/eda_full_20261015"
OUT = f"{ROOT}/run/multilabel_edge_20261023"
os.makedirs(OUT, exist_ok=True)

TARGETS = {  # raw code -> canonical column name
    "P1_MPP": "P1_MPP Missing Primary Package",
    "P1_PPM": "P1_PPM Primary Package Misalignment",
    "P1_COC": "P1_COC Cavity Off Center",
    "P2_FOV": "P2_FOV Field of View Obstructed",
    "F2_FOV": "F2_FOV Field of View Obstructed (production code)",
}
TARGET_CODES = set(TARGETS)
GATES = {"P3_FM_MICRON_THRESHOLD", "P3_FIB_MICRON_THRESHOLD",
         "P3_EP_MICRON_THRESHOLD", "P3_HE_MICRON_THRESHOLD"}


def audit(code_sets):
    """code_sets: picture_md5 -> iterable of codes seen on that picture.
    Returns per-target stats plus the violation rows."""
    stats = {}
    violations = []
    for code, name in TARGETS.items():
        tagged = [m for m, cs in code_sets.items() if code in cs]
        with_extras, gate_only_extra = [], []
        extras_counter = collections.Counter()
        for m in tagged:
            others = cs = code_sets[m]
            extras = {c for c in others
                      if c != code and c not in TARGET_CODES and c not in GATES}
            gates = others & GATES
            if extras:
                with_extras.append(m)
                extras_counter.update(extras)
            elif gates:
                gate_only_extra.append(m)
            if extras or gates:
                violations.append({
                    "picture_md5": m, "standalone_code": code,
                    "extra_codes": ";".join(sorted(extras)),
                    "gate_tags": ";".join(sorted(gates)),
                    "all_codes": ";".join(sorted(others)),
                })
        stats[code] = {
            "name": name,
            "pictures_tagged": len(tagged),
            "pictures_with_extra_labels": len(with_extras),
            "pictures_with_gate_tag_only": len(gate_only_extra),
            "extra_code_counts": dict(sorted(extras_counter.items())),
        }
    return stats, violations


# ---- derivation A: resolved line ----
code_sets_a = collections.defaultdict(set)
with open(f"{EDA}/resolved_labels.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        code_sets_a[r["picture_md5"]].add(r["code"])
stats_a, viol_a = audit(code_sets_a)

# ---- derivation B: raw newer XMLs, all sources ----
name_to_md5s = collections.defaultdict(set)
with open(f"{EDA}/file_manifest.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        name_to_md5s[os.path.basename(r["path"])].add(r["md5"])

newer_xmls = ([f"{ROOT}/data/Updated Annotations 20260922.xml"] +
              sorted(glob.glob(f"{ROOT}/data/annotations_45219[0-4][0-9].xml")))
code_sets_b = collections.defaultdict(set)
unmapped = set()
for xp in newer_xmls:
    for _, el in ET.iterparse(xp, events=("end",)):
        if el.tag == "image":
            base = os.path.basename(el.get("name", ""))
            hits = name_to_md5s.get(base)
            labels = {sh.get("label") for sh in el if sh.get("label")}
            if not hits:
                if labels:
                    unmapped.add(base)
            else:
                for m in hits:
                    code_sets_b[m].update(labels)
            el.clear()
stats_b, viol_b = audit(code_sets_b)

# ---- comparison on the five headline numbers per target ----
cmp_rows = []
for code in sorted(TARGET_CODES):
    a, b = stats_a[code], stats_b[code]
    cmp_rows.append({
        "code": code,
        "tagged_resolved": a["pictures_tagged"], "tagged_raw": b["pictures_tagged"],
        "extras_resolved": a["pictures_with_extra_labels"],
        "extras_raw": b["pictures_with_extra_labels"],
    })

summary = {
    "ticket": "023", "date": "2026-10-23",
    "guide_rule": "Draft 2 sections 4.1-4.4: P1_MPP, P1_PPM, P1_COC, P2_FOV are standalone; no additional tags or labels.",
    "sources": {
        "resolved": f"{EDA}/resolved_labels.csv",
        "raw_newer_xmls": [os.path.basename(x) for x in newer_xmls],
        "raw_unmapped_names_with_labels": len(unmapped),
    },
    "resolved_derivation": stats_a,
    "raw_derivation": stats_b,
    "comparison": cmp_rows,
}
with open(f"{OUT}/standalone_audit.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
with open(f"{OUT}/standalone_violations_resolved.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["picture_md5", "standalone_code", "extra_codes", "gate_tags", "all_codes"])
    w.writeheader(); w.writerows(viol_a)
with open(f"{OUT}/standalone_violations_raw.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["picture_md5", "standalone_code", "extra_codes", "gate_tags", "all_codes"])
    w.writeheader(); w.writerows(viol_b)

print(json.dumps(summary["resolved_derivation"], indent=2))
print("---- raw derivation ----")
print(json.dumps(summary["raw_derivation"], indent=2))
print("---- comparison (resolved vs raw) ----")
for r in cmp_rows:
    print(r)
