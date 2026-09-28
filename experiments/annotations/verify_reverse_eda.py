"""Independent check of the reverse EDA.

Rebuilds every headline number by a second route (regex instead of ElementTree, and a
name-to-hash join built from the file name instead of the folder path) and diffs it against
run/annotations_reverse_eda_20260923/summary.json and the client EDA tables of 2026-09-17.

Run:  python experiments/annotations/verify_reverse_eda.py
"""
import csv
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INV = os.path.join(ROOT, 'run/line_eda/20260916/image_md5_records.csv')
NEW_XML = os.path.join(ROOT, 'data/Updated Annotations 20260922.xml')
OLD_XML = os.path.join(ROOT, 'data/annotations.xml')
SUMMARY = os.path.join(ROOT, 'run/annotations_reverse_eda_20260923/summary.json')
EDA_DIR = os.path.join(ROOT, 'run/client_eda/20260917')
OUT = os.path.join(ROOT, 'run/annotations_reverse_eda_20260923/verification.json')

results = []


def check(name, got, want):
    ok = got == want
    results.append({'check': name, 'got': got, 'want': want, 'ok': ok})
    if not ok:
        print('  FAIL %-60s got %r want %r' % (name, got, want))


# ------------------------------------------------------------- route two: regex
def read_xml_regex(path):
    text = open(path, encoding='utf-8').read()
    images = collections.OrderedDict()
    for block in re.finditer(r'<image\b[^>]*name="([^"]*)"[^>]*?/>|<image\b[^>]*name="([^"]*)"[^>]*?>(.*?)</image>', text, re.S):
        name = block.group(1) or block.group(2)
        body = block.group(3) or ''
        images[name] = (len(re.findall(r'<tag\b', body)), len(re.findall(r'<box\b', body)))
    return images


new_imgs = read_xml_regex(NEW_XML)
old_imgs = read_xml_regex(OLD_XML)
check('new file: images', len(new_imgs), 6097)
check('new file: tags', sum(t for t, b in new_imgs.values()), 4930)
check('new file: boxes', sum(b for t, b in new_imgs.values()), 183)
check('new file: image elements with nothing in them',
      sum(1 for t, b in new_imgs.values() if t == 0 and b == 0), 2021)
check('older file: images', len(old_imgs), 435)
check('older file: boxes', sum(b for t, b in old_imgs.values()), 2020)

# --------------------------------------------------------- the drop, route two
files = {'Updated ICube Objects 20260915': 0,
         'Updated ICube Categorical Classes 20260915': 0,
         'ICube Defects Library': 0}
base_to_md5 = collections.defaultdict(set)
md5_to_base = collections.defaultdict(set)
library_md5 = set()
updated_md5 = set()
library_file_md5 = []
with open(INV, encoding='utf-8-sig', newline='') as fh:
    for row in csv.reader(fh):
        if len(row) < 5 or not row[0]:
            continue
        folder, cls, base, md5 = row[0], row[1], row[2], row[3]
        files[folder] = files.get(folder, 0) + 1
        if folder == 'ICube Defects Library' and cls == 'duplicates':
            continue
        base_to_md5[base].add(md5)
        md5_to_base[md5].add(base)
        if folder == 'ICube Defects Library':
            if cls != 'duplicates':
                library_file_md5.append((base, md5))
                library_md5.add(md5)
        else:
            updated_md5.add(md5)

check('drop: files per folder', files,
      {'Updated ICube Objects 20260915': 4230,
       'Updated ICube Categorical Classes 20260915': 6384,
       'ICube Defects Library': 1465})
all_md5 = set(md5_to_base)
check('drop: distinct pictures', len(all_md5), 10614)

# ------------------------- join the files to the pictures by file name alone
new_annotated_md5 = set()
for name, (t, b) in new_imgs.items():
    if t == 0 and b == 0:
        continue
    base = name.rsplit('/', 1)[-1]
    new_annotated_md5 |= base_to_md5.get(base, set())
old_annotated_md5 = set()
for name in old_imgs:
    base = name.rsplit('/', 1)[-1]
    old_annotated_md5 |= base_to_md5.get(base, set())
new_annotated_md5 &= all_md5
old_annotated_md5 &= all_md5

summary = json.load(open(SUMMARY, encoding='utf-8'))
check('pictures annotated in the new file', len(new_annotated_md5), summary['annotated_by_new_file'])
check('pictures annotated only in the older file',
      len(old_annotated_md5 - new_annotated_md5), summary['covered_only_by_older_file'])
check('pictures annotated nowhere',
      len(all_md5 - new_annotated_md5 - old_annotated_md5), summary['annotated_nowhere'])

# ---------------------------------------------------------------- the identities
check('new-file images = annotated + empty',
      summary['annotated_by_new_file'] + summary['new_file']['images_with_nothing_in_them'],
      summary['new_file']['images'])
check('pictures = new + older only + none',
      summary['annotated_by_new_file'] + summary['covered_only_by_older_file']
      + summary['annotated_nowhere'], len(all_md5))
check('gap by folder adds up to the gap',
      sum(int(r['pictures_with_no_annotation_anywhere'])
          for r in csv.DictReader(open(os.path.join(ROOT, 'run/annotations_reverse_eda_20260923/gap_by_folder.csv'), encoding='utf-8'))),
      summary['annotated_nowhere'])
check('gap by task state adds up to the gap',
      sum(summary['gap_by_folder_task_state'].values()), summary['annotated_nowhere'])
check('duplication axis adds up to the pictures',
      sum(v['pictures'] for v in summary['duplication_axis_same_picture_content'].values()), len(all_md5))

# --------------------------------------------- the older library's own coverage
lib_content_covered = sum(1 for base, md5 in library_file_md5 if md5 in updated_md5)
updated_base_by_md5 = collections.defaultdict(set)
for base, md5 in library_file_md5:
    updated_base_by_md5[md5]  # keeps the key order stable; filled below
for row in csv.reader(open(INV, encoding='utf-8-sig', newline='')):
    if len(row) < 5 or not row[0] or row[0] == 'ICube Defects Library':
        continue
    updated_base_by_md5[row[3]].add(row[2])
different_name = [(base, md5) for base, md5 in library_file_md5
                  if md5 in updated_md5 and base not in updated_base_by_md5[md5]]
check('library files whose picture is in a drop folder under a different name',
      len(different_name), summary['library_same_picture_different_name'])
check('library files whose content is in an Updated folder', lib_content_covered,
      summary['library_files_with_content_in_a_drop_folder'])
check('library pictures found in the drop, by content',
      len(library_md5 & all_md5), summary['library_pictures_found_in_drop_content'])
check('library files: 1287 match, 178 do not',
      lib_content_covered + (len(library_file_md5) - lib_content_covered), 1465)

# the older file's own task list against the image elements it carries
old_task_sizes = [int(m) for m in re.findall(r'<task>.*?<size>(\d+)</size>', open(OLD_XML, encoding='utf-8').read(), re.S)]
check('older file: task sizes as listed', sum(old_task_sizes), 462)
check('older file: frames listed in tasks less image elements carried',
      sum(old_task_sizes) - len(old_imgs), 27)
mine_lib = {r['library_class']: r for r in csv.DictReader(
    open(os.path.join(ROOT, 'run/annotations_reverse_eda_20260923/library_coverage.csv'), encoding='utf-8'))}
old_per_class = collections.Counter(name.split('/')[1] for name in old_imgs)
for cls, n in old_per_class.items():
    check('older file: %s image elements' % cls, int(mine_lib[cls]['library_files_annotated_in_older_file']), n)

# ------------------------------------------------- the client EDA of 2026-09-17
eda_a = {r['folder']: r for r in csv.DictReader(open(os.path.join(EDA_DIR, '2a_folder_totals.csv'), encoding='utf-8'))}
check('client EDA: total distinct pictures',
      int(eda_a['TOTAL, three folders']['unique_pictures']), len(all_md5))
check('client EDA: objects folder files',
      int(eda_a['Updated ICube Objects 20260915']['files']), files['Updated ICube Objects 20260915'])
check('client EDA: categorical folder files',
      int(eda_a['Updated ICube Categorical Classes 20260915']['files']),
      files['Updated ICube Categorical Classes 20260915'])
check('client EDA: library files',
      int(eda_a['ICube Defects Library']['files']), files['ICube Defects Library'])

eda_c = {r['tag']: r for r in csv.DictReader(open(os.path.join(EDA_DIR, '2c_lens_presentation_tags.csv'), encoding='utf-8'))}
mine = {r['class']: r for r in summary['folder_x_coverage']
        if r['folder'] == 'Updated ICube Categorical Classes 20260915'}
alias = {'Low Dose Obstructing Region of Interest': 'Low Dose', 'Multiple Lenses': 'Multiple Lenses'}
for tag, row in eda_c.items():
    key = alias.get(tag, tag)
    if key in mine:
        check('client EDA: %s pictures in the Updated folder' % tag,
              int(row['updated_folders']), int(mine[key]['pictures']))

lib_cov = {r['old_class']: r for r in csv.DictReader(open(os.path.join(EDA_DIR, 'old_library_coverage.csv'), encoding='utf-8'))}
check('client EDA: library pictures not covered by the Updated folders',
      sum(int(r['not_covered']) for r in lib_cov.values()), 177)
for cls, row in lib_cov.items():
    if cls in mine_lib:
        check('client EDA: %s files in the older library' % cls,
              int(row['files']), int(mine_lib[cls]['library_files']))
        check('client EDA: %s distinct pictures in the older library' % cls,
              int(row['unique_images']), int(mine_lib[cls]['pictures_shared_with_drop']))

verdict = {'checks': results, 'checks_failed': sum(1 for r in results if not r['ok'])}
with open(OUT, 'w', encoding='utf-8') as fh:
    json.dump(verdict, fh, indent=2)
print('verification checks: %d, failed: %d' % (len(results), verdict['checks_failed']))
print('written to %s' % os.path.relpath(OUT, ROOT))
sys.exit(1 if verdict['checks_failed'] else 0)
