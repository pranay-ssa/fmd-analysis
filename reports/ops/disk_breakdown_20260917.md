# Shared box disk: full, breakdown and where we can free space (2026-09-17)

Message prepared for the team group. Plain text, self contained, every claim carries its
evidence in the same line.

---

**Shared box disk is at 100%. Here is the breakdown and where we can free space (2026-09-17)**

**Why it matters.** The disk holding the home folders is 123 GB and reached 100% used (605 MB
free). At 100% every new write fails with "No space left on device", and our training saves the
model file at the end of a run, so a run would hold the GPU for an hour and then die on the last
write. Our own pip download cache (3.5 GB) has been cleared, so the disk now sits at 4.1 GB free,
97% used. That is still not enough headroom: the two queued runs need about 3.3 GB.

**Where the 123 GB goes.** Measured with du as root, so no folder is silently skipped.

| Location | Size |
|---|---|
| /home, all users | 115 GB |
| /usr, system | 3.5 GB |
| /var, system logs and package cache | 1.5 GB |
| /tmp | 41 MB |
| free | 4.1 GB |

**Per user.** These numbers are higher than a plain du by a normal user, because parts of other
homes are not readable to us and du skips what it cannot read.

| Home | Size | Biggest items |
|---|---|---|
| srikantht | 83 GB | FMD 3 folders 57 GB, .venv-icube 7.0 GB, ICube Defects 6.9 GB, .cache 4.2 GB, .vscode-server 4.1 GB, preprocessed cropped dataset 3.5 GB |
| pranayp, us | 20 GB | .local 7.9 GB libraries, .vscode-server 3.5 GB, fmd_crop_output 2.9 GB, combined_dataset 2.5 GB, line_experiment 1.2 GB |
| amd100-user | 8.8 GB | .vscode-server 3.8 GB, .cache 3.5 GB, .local 1.5 GB |
| swetap | 3.5 GB | .vscode-server 3.5 GB |

**The single biggest item is a duplicate.** The 57 GB folder "FMD 3 folders" in srikantht's home
holds the three image sets: ICube Defects Library, Updated ICube Categorical Classes 20260915 and
Updated ICube Objects 20260915. The same three sets also sit on the /data disk, which has 367 GB
free. Evidence that it is a copy and not different data: both copies hold 12,079 .bmp files, and
five files taken from the home copy have md5 checksums identical to the same relative path on
/data. Removing it takes the disk from 97% used to about 50%.

| The same three image sets | Pictures | Size |
|---|---|---|
| in srikantht's home, "FMD 3 folders" | 12,079 | 57 GB |
| on /data, in fmd_temp_images, the copy our training reads | 12,079 | 57 GB (6.9 + 20 + 30) |

**Caches, safe to clear because they rebuild themselves.**

| Cache | Size | Owner |
|---|---|---|
| pip download cache | 4.1 GB | srikantht |
| pip download cache | 3.4 GB | amd100-user |
| pip download cache | 3.5 GB cleared today, 45 MB left | pranayp |
| editor remote server files, .vscode-server | 4.1 GB | srikantht |
| editor remote server files, .vscode-server | 3.8 GB | amd100-user |
| editor remote server files, .vscode-server | 3.5 GB | pranayp |
| editor remote server files, .vscode-server | 3.5 GB | swetap |
| package cache and old logs, /var | 0.9 GB | system |

What those two are, in one line each. A pip cache holds downloaded package files so pip need not
download them twice; it refills on demand. The editor files are the VS Code remote server, about
3.4 GB of each copy under .vscode-server/cli; the editor downloads them again the next time that
account connects, so removing them costs one re-download per person and no data.

**What we, pranayp, are freeing.** Our own derived working copies, each rebuildable from the
library.

| Item | Size | What it is |
|---|---|---|
| fmd_crop_output | 2.9 GB | crops cut from the raw frames, 2,930 files |
| combined_dataset_single_20260908 | 2.5 GB | a dataset built from the library, 1,465 pictures plus its split |
| line_experiment_20260917 | 1.2 GB | the five model files from today's finished run |
| OoI_dataset_single | 1.0 GB | a dataset built from the library, 434 pictures plus its split |
| yolo_ooi | 0.6 GB | run artifacts and archives |
| total | 8.2 GB | |

The one judgement call in ours is the 1.2 GB of model files from the run that finished this
morning. Their metrics and confusion matrices are already saved separately, so the weights are
only needed to re-score without retraining, which costs 54 minutes on the GPU.

**What cannot be freed.** The Python environments. /home/pranayp/.local is 7.9 GB and
/home/srikantht/.venv-icube is 7.0 GB, and the five largest single files on the disk are their
libraries: tensorflow 0.95 GB, torch CUDA 0.84 GB, cublas 0.70 GB, cudnn 0.54 GB, a second
tensorflow 0.95 GB. Everything on this box runs through those.

**If everything on this list goes, about 95 GB comes back** and the disk drops from 97% used to
about 20%.

| Action | Freed |
|---|---|
| Remove the duplicate image copy in srikantht's home | 57 GB |
| Clear the four pip caches and the four editor server copies | 22 GB |
| Clear the system package cache and old logs | 0.9 GB |
| Free our own derived copies | 8.2 GB |
| Optional, owner's call: the third copy of the old library, 6.9 GB | 6.9 GB |

**What I am asking.** Whoever owns a copy of data that also lives on /data, please confirm and
free it, which is the 57 GB and possibly the 6.9 GB third copy of the old library. Everyone clear
their own pip cache and editor server files. We are freeing 8.2 GB of our own derived data.

Nothing gets deleted without its owner saying so. This is the map, not the action.

---

## Deletion record: 2026-09-17, the duplicate image copy

**What was removed.** `/home/srikantht/FMD 3 folders`, 57 GB, 12,081 files.

**Who authorised it.** The owner (srikantht) said the folder could go, relayed the same day, on the
basis that he copies data into his home to work on it and clears it afterwards.

**Why it was safe, by measurement and not by assumption.**

| Folder removed | Files | The copy kept, on /data | Files | Compared |
|---|---|---|---|---|
| ICube Defects Library | 1,467 | same folder | 1,467 | same names and sizes |
| Updated ICube Categorical Classes 20260915 | 6,384 | same folder | 6,384 | same names and sizes |
| Updated ICube Objects 20260915 | 4,230 | same folder | 4,230 | same names and sizes |
| **Total** | **12,081** | | **12,081** | every file accounted for |

Every file name and size matched on both sides, and 51 files spread across the set (every 240th
file) had identical md5 checksums. No file was missing on the /data side and no checksum differed.

The kept copy is `/data/FMD_Data_26082026/fmd_temp_images/`, on a disk with 367 GB free, and it is
the copy the per-line training reads, so no split or run file pointed at the removed folder.

**Safeguard used before deleting.** The three folders on /data were each checked for existence and
file count immediately before the delete, and the command aborted if any of them had been absent,
so the last copy could not be removed by mistake.

**Effect.** Free space on the root filesystem went from 3.1 GB to 60 GB, taking it from 98 per cent
used to about 50 per cent. The second candidate in that home, `/home/srikantht/ICube Defects`
(6.9 GB, the same old library with a different internal layout, 1,470 files against 1,467), was
left in place because its equivalence could not be proved the same way.

