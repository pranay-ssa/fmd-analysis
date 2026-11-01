import openpyxl, sys

p = sys.argv[1]
wb = openpyxl.load_workbook(p, data_only=True)
print('SHEETS:', wb.sheetnames)
for ws in wb.worksheets:
    print('\n=== %s (%d x %d) ===' % (ws.title, ws.max_row, ws.max_column))
    n = 0
    for row in ws.iter_rows(values_only=True):
        vals = ['' if v is None else str(v) for v in row]
        if not any(v.strip() for v in vals):
            continue
        n += 1
        if n > 120:
            print('   ... (truncated)')
            break
        print(' | '.join(vals).rstrip(' |'))
