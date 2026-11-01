"""Verify the draft-2 EDA workbook against the computed EDA JSONs (ticket 025)."""
import json
from openpyxl import load_workbook
wb = load_workbook('D:/fmd-analysis/reports/draft2_eda_20261023/draft2_eda_20261023.xlsx')
lp = json.load(open('D:/fmd-analysis/run/draft2_eda_20261023/lp_eda.json'))
ws = wb['LP tags']
errs = []
for i, rec in enumerate(lp['lp_counts'], start=2):
    v = ws.cell(row=i, column=4).value
    if v != rec['pictures']:
        errs.append(('LP', rec['code'], v, rec['pictures']))
ws2 = wb['OOI boxes']
exp = {'Bubble':746,'Bubble Cluster':406,'Wet Package':122,'Surface Groove':0,'Fiber':156,
       'Extraneous Polymer':143,'HEMA (Draft 2 one class)':97,'Foreign Matter':287}
expb = {'Bubble':10070,'Bubble Cluster':1070,'Wet Package':593,'Surface Groove':0,'Fiber':223,
        'Extraneous Polymer':149,'HEMA (Draft 2 one class)':99,'Foreign Matter':579}
for r in range(2, ws2.max_row+1):
    name = ws2.cell(row=r, column=2).value
    if name in exp:
        if ws2.cell(row=r, column=3).value != exp[name]:
            errs.append(('OOI pic', name, ws2.cell(row=r, column=3).value))
        if ws2.cell(row=r, column=5).value != expb[name]:
            errs.append(('OOI boxes', name, ws2.cell(row=r, column=5).value))
print("mismatches:", errs if errs else "none - workbook matches computed JSONs")
print("clear row check:", ws.cell(row=20, column=4).value, "expect 2166")
print("legacy hema check:", ws.cell(row=18, column=4).value, "expect 86")
