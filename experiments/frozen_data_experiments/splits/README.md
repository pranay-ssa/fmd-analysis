---
title: Frozen split
date: 2026-11-19
type: reference
status: active
where: experiments/frozen_data_experiments/splits/README.md
---

# Frozen split

Built 19 November 2026. Population 13,631 pictures. Clear is excluded.

| Split | Pictures | Share |
|---|---:|---:|
| Train | 9,537 | 69.97% |
| Validation | 2,049 | 15.03% |
| Test | 2,045 | 15.00% |

17 columns: 10 lens-presentation classes and 7 object classes. Every row carries at least one label.

`frozen_70_15_15_20261119/`:

- `split.csv`: md5, image path, split. md5 `31a41925e0c349608ff77bf24d801585`.
- `labels_17.csv`: md5, image path, split, 17 label columns. md5 `0d76b29097bc3a95e1b4bb14e9c172cb`.
- `gates_4.csv`: md5, image path, four size flags. Auxiliary, not model outputs. md5 `c97cc04314d2e2b925cdd343e0b80058`.
- `meta.json`: population, duplicate rule, excluded classes, seed, counts, gate totals and file md5.
- `verify_split.py`: recomputes every count from the store. 31 checks pass.
- `verification.txt`: the verifier output.

Builder: `build_frozen_split.py`. Iterative multi-label stratification, seed 42, ratios 70/15/15. The row order is sorted by md5 before assignment, so the split is reproducible.

`build_gates.py` adds `gates_4.csv` from the store tags and records the gate totals in `meta.json`.

Image root on the VM: `/data/FMD_Data_26082026/frozen_data_20261117/images`. All 13,631 paths were checked on the VM and none is missing.
