# Armor blob transfer, 2026-09-16

This record holds the provenance of the two image folders that we moved from the
Armor Azure Blob Storage account to the VM data directory on 2026-09-16.

## Summary

| Item | Value |
|---|---|
| Date of the transfer | 2026-09-16 |
| Source account | Azure Blob Storage, account `stjnjmakearmor` |
| Source container | `fmd-temp` |
| Folders moved | `Updated ICube Objects 20260915/` and `Updated ICube Categorical Classes 20260915/` |
| Images moved | 10,614 |
| Bytes moved | 53,224,773,348 (49.6 GB) |
| Failures | 0 |
| Download time | About 8.6 minutes at 102.7 MB/s average (the script times the download phase) |
| Destination | VM path `/home/amd100-user/FMD_Data_26082026/fmd_temp_images/` |
| Downloader script | repo `vm/ops/download_armor_blobs.py`, VM `~/download_armor_blobs.py` |
| Provenance file | VM `fmd_temp_images/manifest.csv` |

## What we moved

The two folders are the 2026-09-15 update of the ICube defect library. The data
folder names carry that date.

| Folder | Images | Bytes | GB |
|---|---|---|---|
| `Updated ICube Objects 20260915` | 4,230 | 21,211,681,860 | 19.8 |
| `Updated ICube Categorical Classes 20260915` | 6,384 | 32,013,091,488 | 29.8 |
| **Total** | **10,614** | **53,224,773,348** | **49.6** |

### Subfolder counts

`Updated ICube Objects 20260915` holds five folders. It groups images by object
type.

| Subfolder | Images |
|---|---|
| Clear | 2,333 |
| Foreign Matter | 1,282 |
| Fiber | 328 |
| Extraneous Polymer | 267 |
| HEMA | 20 |

`Updated ICube Categorical Classes 20260915` holds thirteen folders. It groups
images by defect class.

| Subfolder | Images |
|---|---|
| Low Dose | 1,952 |
| Multiple Lenses | 1,439 |
| Missing Primary Package | 1,427 |
| Missing Lens | 324 |
| Package Misalignment | 293 |
| Lens Off Center | 258 |
| Cavity Off Center | 183 |
| HEMA Obstruction | 175 |
| duplicates | 143 |
| View Obstructed | 117 |
| Dirty Strobe | 42 |
| Dirty Camera | 25 |
| Bubble Scatter | 6 |

### File format

Every image in both folders has the same format.

| Property | Value |
|---|---|
| Type | BMP, 8-bit grayscale |
| Pixels | 2,048 wide, 2,448 high |
| File size | 5,014,582 bytes each |
| Header | 1,078 bytes |
| Pixel data | 5,013,504 bytes |

The file size is constant, so the total is exact: 10,614 times 5,014,582 equals
53,224,773,348 bytes.

## Destination and layout

The downloader keeps the blob folder name as the local folder name. The files
therefore land in two new top-level folders inside `fmd_temp_images`:

```
/home/amd100-user/FMD_Data_26082026/fmd_temp_images/
├── Updated ICube Objects 20260915/
├── Updated ICube Categorical Classes 20260915/
├── manifest.csv
├── 20260826_T24_Production_Sample/     (already present)
├── ICube Defects Library/              (already present)
├── Package Find Test/                  (already present)
├── Ripple Obstruction/                 (already present)
├── Utils/                              (already present)
└── YOLO26_ICube_Defects/               (already present)
```

This layout matches the container. Each container root folder has a folder of the
same name on the VM.

`/home/amd100-user/FMD_Data_26082026` is a symbolic link to
`/data/FMD_Data_26082026`. The destination is therefore on the `/data` volume
(`/dev/sda1`, ext4), not on the root volume. The `/data` volume went from 62 GB
used to 112 GB used. It had 367 GB free after the transfer.

## Scripts and credentials

| Item | Location |
|---|---|
| Downloader, repo copy | `vm/ops/download_armor_blobs.py` |
| Downloader, VM copy | `/home/amd100-user/download_armor_blobs.py` |
| Connection string, local | `C:/Users/HP/.fmd/armor_blob_conn` |
| Connection string, VM | `/home/amd100-user/armor_blob_conn`, mode 600 |
| Run log, VM | `/home/amd100-user/armor_download.log` |

The script reads the connection string from the environment variable
`ARMOR_BLOB_CONNECTION_STRING` first. It reads the credential file second. The
file can hold a full connection string or a bare account key. The repository
holds no key.

The script protects the data in four ways.

1. A dry run lists the files and writes nothing. It fails with exit code 2 when a
   folder name matches no blob. This catches a typing error in a folder name,
   which would otherwise look like a successful run.
2. Each file lands as `<name>.part` first. The script checks the size and the MD5
   against the value from the service. It then renames the file in one step. A
   failed transfer leaves no partial file, so a later run retries that file.
3. The script retries each file three times. Each file uses four parallel streams.
4. The script writes `manifest.csv` with the name, path, byte count, etag, MD5 and
   status of each file. It writes `manifest_failures.csv` when a file fails.

### How to run it again

Run these commands on the VM as `amd100-user`.

```bash
cd ~
python3 download_armor_blobs.py --conn-file ~/armor_blob_conn --dry-run
python3 -u download_armor_blobs.py --conn-file ~/armor_blob_conn
```

The defaults cover this transfer: the two folders above, the destination above,
8 parallel downloads and 3 attempts. A second run skips the files that are
already on disk. Use `--overwrite` to download them again.

| Flag | Effect |
|---|---|
| `--dry-run` | List the work. Write nothing. |
| `--dest DIR` | Change the destination. |
| `--prefix P` | Change a source folder. Repeat the flag for more than one folder. |
| `--strip-prefix` | Drop the blob folder name from the local path. This merges the folders. |
| `--overwrite` | Download files that are already on disk. |
| `--limit N` | Download at most N files. Use it for a test. |
| `--dump-names FILE` | Write every matched blob name and size to a CSV, then stop. |
| `--jobs N` | Change the number of parallel downloads. |
| `--no-md5` | Skip the MD5 check. The size check still runs. |

## Verification

We checked the result in three independent ways. None of these checks uses the
word of the downloader.

| Check | Method | Result |
|---|---|---|
| File count | Count the files on disk for each folder | 4,230 and 6,384. Total 10,614. Matches the source listing. |
| Byte total | Sum the bytes on disk | 21,211,681,860 and 32,013,091,488. Total 53,224,773,348. Byte-exact against the source listing. |
| File content | Read every file from disk again and compare its MD5 with the service value | 10,614 of 10,614 OK. `md5sum -c` returned exit code 0. |
| Partial files | Search for `*.part` | 0 |
| Failures | Look for the failures file | Not created, so no file failed. |
| Manifest | Count the lines | 10,615 lines: one header and 10,614 records. |
| Dry run on the VM | Run the script with `--dry-run` before the transfer | The VM reported the same counts and the same byte total as the local check. |

The MD5 check is the strongest of these. All 10,614 blobs carry a `content_md5`
value from the service. The script checked each value during the transfer. We then
read each file from disk and checked the value again.

## Known issues in the data

1. The `duplicates` subfolder holds 143 images. The source library marks these as
   duplicates. Do not train on them without a decision.
2. 27 image names appear in both folders. 2 more names repeat inside the
   categorical folder. A merged training set would hold those images twice. We
   ruled out duplicate leakage on the earlier combined 22-class set, so this
   needs a decision before any training run.
3. The folder `Updated ICube Categorical Classes 20260915/` holds a file named
   `cross_directory_duplicates.csv`. It is 31 bytes: the header row
   `file_hash,class_dir,file_path` and no records. It certifies nothing. Our own
   check is the evidence for point 2.
4. The two folders use different taxonomies. `Objects` groups by object type.
   `Categorical Classes` groups by defect class. They are two labels for the same
   library, not two halves of one dataset.
5. The downloader skips files that are not images. One such file exists in the
   source: the 31-byte CSV above. No image file was skipped.

## Container facts

| Item | Value |
|---|---|
| Blobs in the container | 22,156 |
| Root folders | `20260826_T24_Production_Sample`, `ICube Defects Library`, `Updated ICube Categorical Classes 20260915`, `Updated ICube Objects 20260915`, `Utils` |
| Public access | Off. An anonymous request returns HTTP 409, "Public access is not permitted". |
| Endpoint | `https://stjnjmakearmor.blob.core.windows.net` |

We did not move the other root folders. `ICube Defects Library` is already on the
VM. `20260826_T24_Production_Sample` holds 10,000 blobs (46.7 GB). `Utils` holds
73 blobs.

## Security note

The file `/data/FMD_Data_26082026/blob_migrate_two.py` holds two storage account
keys in plain text: `stjnjmakearmor` and `sashield`. The file mode is 664. The VM
is shared with the accounts `amd100-user`, `ksurampudi`, `linuxadmin`, `pranayp`,
`srikantht` and `swetap`. Every account on the VM can read both keys. The keys do
not expire. The file `/data/FMD_Data_26082026/download_fmd.py` holds the
`stjnjmakearmor` key in the same way. We recommend that you move both keys to a
file with mode 600, and that you rotate the keys.

The downloader in this record stores no key. It reads the key from a file with
mode 600.

## Related work on the VM

The folder `/data/FMD_Data_26082026` holds earlier scripts for the same account:
`download_fmd.py` (2026-08-27) and `blob_migrate_two.py` (2026-08-27). The script
that came up for review was a copy of `download_fmd.py` with a folder filter
added. `blob_migrate_two.py` copies blobs from `stjnjmakearmor` to a second
account, `sashield`, container `fmd-data`, with a server-side copy. Use that route
if these two folders must also reach the `sashield` account. A server-side copy
does not pass the data through the VM.
