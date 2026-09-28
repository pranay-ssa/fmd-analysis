"""Reverse EDA: does every picture in the drop carry an annotation, in the new file or the older one?

Reads three records and joins them on picture content:
  1. run/line_eda/20260916/image_md5_records.csv   - the drop, one row per image file, with md5
  2. data/Updated Annotations 20260922.xml         - the new CVAT export (tags and boxes)
  3. data/annotations.xml                          - the older ICube Defects Library (boxes only)

Writes run/annotations_reverse_eda_20260923/:
  picture_coverage.csv   one row per distinct picture
  folder_x_coverage.csv  one row per drop class folder
  gap_pictures.csv       every picture with no annotation anywhere
  gap_by_library_class.csv  the gap, read against the older library's classes
  library_coverage.csv   what the older library adds to the drop
  summary.json           headline numbers, plus self-checks

Run:  python experiments/annotations/reverse_eda_annotation_coverage.py
"""
import collections
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INV = os.path.join(ROOT, 'run/line_eda/20260916/image_md5_records.csv')
NEW_XML = os.path.join(ROOT, 'data/Updated Annotations 20260922.xml')
OLD_XML = os.path.join(ROOT, 'data/annotations.xml')
OUT = os.path.join(ROOT, 'run/annotations_reverse_eda_20260923')

LIBRARY_FOLDER = 'ICube Defects Library'
OBJECTS_FOLDER = 'Updated ICube Objects 20260915'
CATEGORICAL_FOLDER = 'Updated ICube Categorical Classes 20260915'
DUPLICATES_CLASS = 'duplicates'

checks = []


def check(name, got, want):
    ok = got == want
    checks.append({'check': name, 'got': got, 'want': want, 'ok': ok})
    if not ok:
        print('  FAIL %-52s got %r want %r' % (name, got, want))
    return ok


# ---------------------------------------------------------------- 1. the drop
inventory = []
with open(INV, encoding='utf-8-sig', newline='') as fh:
    for row in csv.reader(fh):
        if len(row) < 5 or not row[0]:
            continue
        inventory.append({'folder': row[0], 'cls': row[1], 'base': row[2],
                          'md5': row[3], 'size': row[4]})

print('drop inventory: %d image files' % len(inventory))
by_path = {}
by_folder_base = collections.defaultdict(list)
by_base = collections.defaultdict(list)
for row in inventory:
    by_path.setdefault((row['folder'], row['cls'], row['base']), []).append(row)
    by_folder_base[(row['folder'], row['base'])].append(row)
    by_base[row['base']].append(row)

dataset = [r for r in inventory if not (r['folder'] == CATEGORICAL_FOLDER and r['cls'] == DUPLICATES_CLASS)]
dup_rows = [r for r in inventory if r['folder'] == CATEGORICAL_FOLDER and r['cls'] == DUPLICATES_CLASS]
check('duplicates subfolder rows', len(dup_rows), 143)
check('dataset files (duplicates excluded)', len(dataset), 11936)


# ------------------------------------------------------------ 2. the two files
def read_cvat(path):
    """image name -> {'tags': [...], 'boxes': [...]}"""
    root = ET.parse(path).getroot()
    out = {}
    for img in root.findall('image'):
        name = img.get('name')
        out[name] = {
            'tags': [t.get('label') for t in img.findall('tag')],
            'boxes': [b.get('label') for b in img.findall('box')],
        }
    return out


new_xml = read_cvat(NEW_XML)
old_xml = read_cvat(OLD_XML)
n_new_tags = sum(len(v['tags']) for v in new_xml.values())
n_new_boxes = sum(len(v['boxes']) for v in new_xml.values())
n_old_boxes = sum(len(v['boxes']) for v in old_xml.values())
print('new file: %d images, %d tags, %d boxes' % (len(new_xml), n_new_tags, n_new_boxes))
print('older file: %d images, %d boxes' % (len(old_xml), n_old_boxes))
check('new file images', len(new_xml), 6097)
check('new file tags', n_new_tags, 4930)
check('new file boxes', n_new_boxes, 183)
check('older file images', len(old_xml), 435)
check('older file boxes', n_old_boxes, 2020)


# --------------------------------------------------- 3. name -> inventory row
def resolve(name):
    """Return (rows, method) for a CVAT image name."""
    parts = name.split('/')
    if len(parts) < 3:
        return [], 'short-name'
    folder, cls, base = parts[0], parts[1], '/'.join(parts[2:])
    hit = by_path.get((folder, cls, base))
    if hit:
        return hit, 'path'
    hit = by_folder_base.get((folder, base))
    if hit:
        return hit, 'folder+base'
    hit = by_base.get(base)
    if hit and len(hit) == 1:
        return hit, 'base'
    return [], 'unmatched'


new_match_method = collections.Counter()
new_row_by_name = {}
for name in new_xml:
    rows, method = resolve(name)
    new_match_method[method] += 1
    if rows:
        new_row_by_name[name] = rows[0]

old_match_method = collections.Counter()
old_row_by_name = {}
for name in old_xml:
    rows, method = resolve(name)
    old_match_method[method] += 1
    if rows:
        old_row_by_name[name] = rows[0]

print('new file name resolution:', dict(new_match_method))
print('older file name resolution:', dict(old_match_method))
check('every new-file image resolved', new_match_method['unmatched'], 0)
check('every older-file image resolved by full path', old_match_method['path'], len(old_xml))


# ------------------------------------------------------- 4. per picture facts
pictures = collections.OrderedDict()          # md5 -> record
for row in dataset:
    rec = pictures.setdefault(row['md5'], {
        'md5': row['md5'], 'locations': [], 'new_tags': [], 'new_boxes': [],
        'old_boxes': [], 'old_classes': [], 'in_new_file': False, 'in_old_file': False,
        'size': row['size'],
    })
    rec['locations'].append((row['folder'], row['cls'], row['base']))

for name, ann in new_xml.items():
    row = new_row_by_name.get(name)
    if row is None:
        continue
    rec = pictures.get(row['md5'])
    if rec is None:                       # picture only reachable through the duplicates folder
        continue
    rec['in_new_file'] = True
    rec['new_tags'].extend(ann['tags'])
    rec['new_boxes'].extend(ann['boxes'])

old_annotated_paths = {name: row for name, row in old_row_by_name.items()}
for name, ann in old_xml.items():
    row = old_row_by_name.get(name)
    if row is None:
        continue
    rec = pictures.get(row['md5'])
    if rec is None:
        continue
    rec['in_old_file'] = True
    rec['old_boxes'].extend(ann['boxes'])
    rec['old_classes'].append(row['cls'])

# a picture may be reachable only via the duplicates folder: report those separately
dupe_md5 = {r['md5'] for r in dup_rows}
orphan_md5 = {m for m in dupe_md5 if m not in pictures}
print('pictures only in the duplicates folder: %d' % len(orphan_md5))

for rec in pictures.values():
    has_new = bool(rec['new_tags'] or rec['new_boxes'])
    if has_new and rec['new_tags'] and rec['new_boxes']:
        rec['status'] = 'new_tag_and_box'
    elif has_new and rec['new_boxes']:
        rec['status'] = 'new_box_only'
    elif has_new:
        rec['status'] = 'new_tag_only'
    elif rec['in_old_file']:
        rec['status'] = 'older_library_only'
    else:
        rec['status'] = 'none'

status_counts = collections.Counter(r['status'] for r in pictures.values())
print('pictures: %d' % len(pictures))
for k in ('new_tag_and_box', 'new_box_only', 'new_tag_only', 'older_library_only', 'none'):
    print('  %-20s %5d' % (k, status_counts[k]))

annotated_new = sum(v for k, v in status_counts.items() if k.startswith('new_'))
check('pictures with a new-file annotation', annotated_new,
      sum(1 for r in pictures.values() if r['in_new_file'] and (r['new_tags'] or r['new_boxes'])))
check('pictures = annotated in new + older only + none',
      annotated_new + status_counts['older_library_only'] + status_counts['none'], len(pictures))

# every new-file image element must be either empty or carry something, and we
# should account for all 6,097 of them
empty_new_images = sum(1 for v in new_xml.values() if not v['tags'] and not v['boxes'])
print('new-file image elements with nothing in them: %d' % empty_new_images)


# --------------------------------------------------------------- 5. the tables
os.makedirs(OUT, exist_ok=True)

# 5a. one row per picture
with open(os.path.join(OUT, 'picture_coverage.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['md5', 'status', 'n_locations', 'folders', 'classes', 'basenames',
                'new_tags', 'new_boxes', 'old_boxes', 'old_classes', 'size'])
    for rec in pictures.values():
        w.writerow([rec['md5'], rec['status'], len(rec['locations']),
                    '|'.join(sorted({l[0] for l in rec['locations']})),
                    '|'.join(sorted({l[1] for l in rec['locations']})),
                    '|'.join(sorted({l[2] for l in rec['locations']})),
                    '|'.join(rec['new_tags']), '|'.join(rec['new_boxes']),
                    '|'.join(rec['old_boxes']), '|'.join(sorted(set(rec['old_classes']))),
                    rec['size']])

# 5b. one row per drop class folder — the reverse-EDA table
folder_order = []
seen = set()
for row in dataset:
    key = (row['folder'], row['cls'])
    if key not in seen:
        seen.add(key)
        folder_order.append(key)

def in_folder(rec, folder, cls):
    return any(l[0] == folder and l[1] == cls for l in rec['locations'])


# which drop class folders the new file actually has a task for
has_task = collections.Counter()
for name in new_xml:
    parts = name.split('/')
    if len(parts) >= 3:
        has_task[(parts[0], parts[1])] += 1


folder_rows = []
for folder, cls in folder_order:
    recs = [r for r in pictures.values() if in_folder(r, folder, cls)]
    n_new = sum(1 for r in recs if r['status'].startswith('new_'))
    n_new_tag = sum(1 for r in recs if r['new_tags'])
    n_new_box = sum(1 for r in recs if r['new_boxes'])
    n_old_only = sum(1 for r in recs if r['status'] == 'older_library_only')
    n_none = sum(1 for r in recs if r['status'] == 'none')
    files = sum(1 for r in dataset if r['folder'] == folder and r['cls'] == cls)
    folder_rows.append({
        'folder': folder, 'class': cls, 'image_files': files, 'pictures': len(recs),
        'has_a_task_in_the_new_file': has_task[(folder, cls)],
        'pictures_with_new_tag': n_new_tag, 'pictures_with_new_box': n_new_box,
        'pictures_with_new_annotation': n_new,
        'pictures_covered_by_older_library_only': n_old_only,
        'pictures_with_no_annotation_anywhere': n_none,
    })
    check('rows add up for %s/%s' % (folder, cls), n_new + n_old_only + n_none, len(recs))

with open(os.path.join(OUT, 'folder_x_coverage.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(folder_rows[0].keys()))
    w.writeheader()
    w.writerows(folder_rows)

# 5c. the gap, one row per picture
gap = [r for r in pictures.values() if r['status'] == 'none']
with open(os.path.join(OUT, 'gap_pictures.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['md5', 'n_locations', 'folders', 'classes', 'basenames', 'size'])
    for rec in sorted(gap, key=lambda r: (r['locations'][0][0], r['locations'][0][1], r['locations'][0][2])):
        w.writerow([rec['md5'], len(rec['locations']),
                    '|'.join(sorted({l[0] for l in rec['locations']})),
                    '|'.join(sorted({l[1] for l in rec['locations']})),
                    '|'.join(sorted({l[2] for l in rec['locations']})),
                    rec['size']])

# 5d. the gap against the older library's own classes
lib_by_md5 = collections.defaultdict(list)
for row in inventory:
    if row['folder'] == LIBRARY_FOLDER:
        lib_by_md5[row['md5']].append(row)
old_lib_paths = set(old_xml)

gap_lib = collections.Counter()
for rec in gap:
    for lrow in lib_by_md5.get(rec['md5'], []):
        key = lrow['cls'] + (' (annotated in the older file)' if
                             LIBRARY_FOLDER + '/' + lrow['cls'] + '/' + lrow['base'] in old_lib_paths
                             else ' (in the library, not annotated)')
        gap_lib[key] += 1
with open(os.path.join(OUT, 'gap_by_library_class.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['library_class_and_state', 'pictures'])
    for k, v in gap_lib.most_common():
        w.writerow([k, v])

# 5e. what the older library adds
lib_rows = []
for cls, n in sorted(collections.Counter(r['cls'] for r in inventory
                                         if r['folder'] == LIBRARY_FOLDER).items()):
    recs = [r for r in pictures.values() if in_folder(r, LIBRARY_FOLDER, cls)]
    lib_files = [r for r in inventory if r['folder'] == LIBRARY_FOLDER and r['cls'] == cls]
    lib_paths = {LIBRARY_FOLDER + '/' + r['cls'] + '/' + r['base'] for r in lib_files}
    lib_rows.append({
        'library_class': cls,
        'library_files': len(lib_files),
        'library_files_annotated_in_older_file': len(lib_paths & old_lib_paths),
        'pictures_shared_with_drop': len(recs),
        'pictures_annotated_in_new_file': sum(1 for r in recs if r['status'].startswith('new_')),
        'pictures_annotated_only_in_older_file': sum(1 for r in recs if r['status'] == 'older_library_only'),
        'pictures_annotated_nowhere': sum(1 for r in recs if r['status'] == 'none'),
    })
with open(os.path.join(OUT, 'library_coverage.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(lib_rows[0].keys()))
    w.writeheader()
    w.writerows(lib_rows)

# 5f. the duplication axis: is the picture a repeat of one the older library holds?
lib_md5 = set(lib_by_md5)
lib_base_norm = {}
for row in inventory:
    if row['folder'] == LIBRARY_FOLDER:
        lib_base_norm.setdefault(row['base'], set()).add(row['md5'])

axis = collections.OrderedDict()
for label, pred in (
    ('repeat of a picture the older library holds', lambda r: r['md5'] in lib_md5),
    ('no copy in the older library', lambda r: r['md5'] not in lib_md5),
):
    recs = [r for r in pictures.values() if pred(r)]
    axis[label] = {
        'pictures': len(recs),
        'annotated_in_the_new_file': sum(1 for r in recs if r['status'].startswith('new_')),
        'annotated_only_in_the_older_file': sum(1 for r in recs if r['status'] == 'older_library_only'),
        'annotated_nowhere': sum(1 for r in recs if r['status'] == 'none'),
    }

# name-based view of the same question, for comparison. A library file whose content
# is in a drop folder under a different name is invisible to name matching.
lib_names = set(lib_base_norm)
by_md5_in_updated = collections.defaultdict(set)
for row in inventory:
    if row['folder'] != LIBRARY_FOLDER:
        by_md5_in_updated[row['md5']].add(row['base'])
updated_md5 = set(by_md5_in_updated)
same_content_other_name = []
n_lib_content_in_drop = n_lib_name_in_drop = 0
for row in inventory:
    if row['folder'] != LIBRARY_FOLDER:
        continue
    if row['md5'] in updated_md5:
        n_lib_content_in_drop += 1
        if row['base'] in by_md5_in_updated[row['md5']]:
            n_lib_name_in_drop += 1
        else:
            same_content_other_name.append((row['cls'], row['base'],
                                            sorted(by_md5_in_updated[row['md5']])))
with open(os.path.join(OUT, 'library_same_picture_different_name.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['library_class', 'library_file_name', 'drop_file_names_for_the_same_picture'])
    for cls, base, other in same_content_other_name:
        w.writerow([cls, base, '|'.join(other)])
name_matched = {r['md5'] for r in pictures.values()
                if any(l[2] in lib_names and l[0] == LIBRARY_FOLDER for l in r['locations'])}
content_matched = set(lib_md5) & {r['md5'] for r in pictures.values()}
print('library files whose picture sits in a drop folder under a different name: %d' % len(same_content_other_name))

with open(os.path.join(OUT, 'duplication_axis.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['definition', 'group', 'pictures', 'annotated_in_the_new_file',
                'annotated_only_in_the_older_file', 'annotated_nowhere'])
    for definition, table in (('same picture content', axis),):
        for group, vals in table.items():
            w.writerow([definition, group, vals['pictures'], vals['annotated_in_the_new_file'],
                        vals['annotated_only_in_the_older_file'], vals['annotated_nowhere']])


# 5g. where the older library's annotated pictures sit in the drop
lib_x_drop = collections.Counter()
for name, ann in old_xml.items():
    row = old_row_by_name.get(name)
    if row is None:
        continue
    rec = pictures.get(row['md5'])
    if rec is None:
        continue
    for loc in rec['locations']:
        if loc[0] != LIBRARY_FOLDER:
            lib_x_drop[(row['cls'], loc[1], rec['status'])] += 1
with open(os.path.join(OUT, 'library_pictures_in_drop.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['library_class', 'drop_class_folder', 'picture_status_in_the_new_file', 'pictures'])
    for (lcls, dcls, status), n in sorted(lib_x_drop.items()):
        w.writerow([lcls, dcls, status, n])

# 5h. the gap, split by whether the drop folder has a task in the new file at all
gap_by_task = collections.Counter()
for rec in pictures.values():
    if rec['status'] != 'none':
        continue
    if any(has_task[loc[:2]] for loc in rec['locations'] if loc[0] != LIBRARY_FOLDER):
        gap_by_task['folder the new file has a task for'] += 1
    else:
        gap_by_task['folder the new file has no task for'] += 1
print('gap by task state:', dict(gap_by_task))


# 5i. the gap, one row per drop class folder, each picture counted once
gap_primary = collections.Counter()
gap_multi = 0
for rec in gap:
    nonlib = [l for l in rec['locations'] if l[0] != LIBRARY_FOLDER]
    if not nonlib:
        gap_primary[('ICube Defects Library', rec['locations'][0][1])] += 1
    else:
        if len(nonlib) > 1:
            gap_multi += 1
        nonlib.sort()
        gap_primary[(nonlib[0][0], nonlib[0][1])] += 1
order = {k: i for i, k in enumerate(folder_order)}
with open(os.path.join(OUT, 'gap_by_folder.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.writer(fh)
    w.writerow(['folder', 'class', 'pictures_with_no_annotation_anywhere'])
    for (folder, cls), n in sorted(gap_primary.items(), key=lambda kv: -kv[1]):
        w.writerow([folder, cls, n])
check('gap by folder adds up', sum(gap_primary.values()), len(gap))
print('gap pictures sitting in more than one drop folder: %d' % gap_multi)


# ------------------------------------------------------------- 6. the summary
summary = {
    'source': {'inventory': 'run/line_eda/20260916/image_md5_records.csv',
               'new_annotations': 'data/Updated Annotations 20260922.xml',
               'older_annotations': 'data/annotations.xml'},
    'drop': {
        'image_files': len(inventory),
        'dataset_image_files': len(dataset),
        'duplicates_subfolder_files': len(dup_rows),
        'distinct_pictures_dataset': len(pictures),
        'files_per_folder': dict(collections.Counter(r['folder'] for r in inventory)),
    },
    'new_file': {'images': len(new_xml), 'tags': n_new_tags, 'boxes': n_new_boxes,
                 'images_with_nothing_in_them': empty_new_images,
                 'name_resolution': dict(new_match_method)},
    'older_file': {'images': len(old_xml), 'boxes': n_old_boxes,
                   'name_resolution': dict(old_match_method)},
    'picture_status': dict(status_counts),
    'annotated_by_new_file': annotated_new,
    'covered_only_by_older_file': status_counts['older_library_only'],
    'annotated_nowhere': status_counts['none'],
    'share_of_pictures_with_an_annotation':
        round((annotated_new + status_counts['older_library_only']) / len(pictures), 4),
    'pictures_only_in_duplicates_folder': len(orphan_md5),
    'folder_x_coverage': folder_rows,
    'library_coverage': lib_rows,
    'duplication_axis_same_picture_content': axis,
    'library_same_picture_different_name': len(same_content_other_name),
    'library_files_with_content_in_a_drop_folder': n_lib_content_in_drop,
    'library_files_with_the_same_name_in_a_drop_folder': n_lib_name_in_drop,
    'gap_by_folder_task_state': dict(gap_by_task),
    'library_pictures_found_in_drop_content': len(content_matched),
    'library_pictures_found_in_drop_by_name': len(name_matched),
    'checks': checks,
    'checks_failed': sum(1 for c in checks if not c['ok']),
}
with open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8') as fh:
    json.dump(summary, fh, indent=2)

print()
print('checks: %d, failed: %d' % (len(checks), summary['checks_failed']))
print('pictures with an annotation: %d of %d (%.1f%%)'
      % (annotated_new + status_counts['older_library_only'], len(pictures),
         100.0 * (annotated_new + status_counts['older_library_only']) / len(pictures)))
print('written to %s' % os.path.relpath(OUT, ROOT))
sys.exit(1 if summary['checks_failed'] else 0)
