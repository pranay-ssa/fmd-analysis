# USB checklist — old laptop → this laptop (2026-09-17)

Take this file with you to the old laptop. Everything on it is read-only; nothing on the old laptop
gets changed or deleted.

**Confirmed by the user:** the old laptop is reachable (USB drive or LAN) and the SSH key passphrases
are known. So this is the clean path — nothing has to be re-derived.

---

## A. Before you go — copy the kit to the old laptop

You need two files on the old laptop; they were written here and the old laptop does not have them.

| File | Size |
|---|---|
| `docs/transfer/pack_old_laptop.sh` | 8.6 KB |
| `docs/transfer/restore_new_laptop.sh` (not needed there, but keep them together) | 10 KB |

Put them anywhere on the old laptop — email them to yourself, or drop them on the USB stick. Say they
land in `D:\kit\`.

## B. On the old laptop (USB drive plugged in as `E:` — check the letter)

Open **Git Bash** (right-click in the `D:\kit` folder → *Open Git Bash here*), then:

```bash
OUT="E:/fmd-transfer" bash pack_old_laptop.sh
```

Defaults it will use, and how to override each:

| Setting | Default | Override |
|---|---|---|
| Repo | `D:/02-SSA/fmd-analysis` | `REPO="D:/other/path"` |
| Old home | `C:/Users/HP` | `OLDHOME="C:/Users/other"` |
| Output | `D:/fmd-transfer` | `OUT="E:/fmd-transfer"` (a USB drive) |
| Image library (7 GB) | included | `SKIP_DATA=1` to leave it out |
| Crops (6.4 GB) | **skipped** | `SKIP_CROPS=0` to include them — **not needed**, the VM already has the crops |

Expected result: `E:/fmd-transfer/fmd-transfer-<date>/` with a pack size of about **7-8 GB**, and
`SHA256SUMS` at the end. The script prints the pack size when it finishes.

It collects: a `git bundle` of every branch, the untracked working-tree files, the uncommitted diff,
`/c/Users/HP/.ssh`, the blob connection file, the Hermes profile, `data/incoming`, all
`runs/**/weights/*.pt`, and `notes/INVENTORY.txt` with the old laptop's own counts.

Write down two numbers from `notes/INVENTORY.txt` before you leave:
**`data/incoming BMPs`** and **`runs/**/weights .pt`**. You will compare them on the other side.

## C. If Git Bash on the old laptop is a problem — manual copy

Copy these five things onto the USB stick by hand, in this order. The repo folder is the important one.

| # | Copy from the old laptop | To this laptop | Size |
|---|---|---|---|
| 1 | the **whole repo folder**, `.git` included (that is what carries the 10 unpushed commits) | `D:\fmd-analysis` | ~500 MB + 13 MB git |
| 2 | `C:\Users\HP\.ssh` | `C:\Users\Abcom\.ssh` | tiny |
| 3 | `C:\Users\HP\.fmd\armor_blob_conn` | `C:\Users\Abcom\.fmd\` | tiny |
| 4 | `C:\Users\HP\AppData\Local\hermes` — at least `memories`, `skills`, `SOUL.md`, `config.yaml`, `state.db` | `%LOCALAPPDATA%\hermes` | tens of MB |
| 5 | `data\incoming` — 22 class folders, 1,465 BMPs | `D:\fmd-analysis\data\incoming` | ~7 GB |

**Do not let Windows merge-copy the repo blindly.** This laptop's working tree carries edits dated
2026-09-17 and copying an older file over a newer one is a silent regression. Either use
`restore_new_laptop.sh` (it stages instead of overwriting), or copy with
`robocopy <usb>\fmd-analysis D:\fmd-analysis /E /XC /XN /XO` (`/XO` = leave older files alone).

## D. Back here

```bash
bash docs/transfer/restore_new_laptop.sh /d/fmd-transfer/fmd-transfer-<date>
```

It verifies the checksums, installs the keys, rewrites `C:/Users/HP` → `C:/Users/Abcom` in the ssh
config, extracts the data, and stages the untracked work with a NEW/DIFFERS/identical classification.
Then it prints the verification block — compare its `data/incoming BMPs` and weights counts against
the two numbers you wrote down.

## E. Then, in this order

1. **`ssh fmd-vm`** (or `amd-a100-vm`) — confirm the key and the passphrase still work.
2. **Push the commits**: `git push -u origin master`. Git Credential Manager will ask you to sign in
   through the browser. If it says *Repository not found* **after** a successful sign-in, the repo is
   gone and needs recreating — create an empty private repo and
   `git remote set-url origin <new-url>` first.
3. **Do not wipe the old laptop** until the numbers in step D match and the push in step 2 has landed.
